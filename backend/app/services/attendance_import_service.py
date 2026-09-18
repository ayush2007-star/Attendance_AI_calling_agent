from datetime import date
from io import BytesIO
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.absence import AbsenceEvent
from app.models.attendance import AttendanceRecord
from app.models.attendance_import import AttendanceImportBatch
from app.models.attendance_summary import AttendanceSummary
from app.models.student import Student
from app.models.user import User
from app.schemas.attendance_import import AttendanceImportCreate
from app.services.attendance_excel_parser import parse_attendance_workbook
from app.services.class_service import get_class


MAX_UPLOAD_SIZE = 10 * 1024 * 1024


def create_import_batch(
    db: Session,
    data: AttendanceImportCreate,
    uploaded_by: User,
) -> AttendanceImportBatch:
    if data.class_id is None and uploaded_by.role != "SUPER_ADMIN":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A class is required for scoped attendance imports",
        )

    if data.class_id is not None:
        class_obj = get_class(db, data.class_id, uploaded_by)
        if class_obj is None or not class_obj.is_active:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Selected class does not exist or is inactive",
            )

    import_batch = AttendanceImportBatch(
        file_name=data.file_name,
        file_type=data.file_type,
        attendance_date=data.attendance_date,
        class_id=data.class_id,
        total_rows=0,
        valid_rows=0,
        invalid_rows=0,
        duplicate_rows=0,
        status="PROCESSING",
        uploaded_by=uploaded_by.id,
    )

    db.add(import_batch)
    db.commit()
    db.refresh(import_batch)

    return import_batch


def process_attendance_upload(
    db: Session,
    file_name: str,
    file_content: bytes,
    attendance_date: date,
    class_id: UUID | None,
    uploaded_by: User,
) -> AttendanceImportBatch:
    if len(file_content) > MAX_UPLOAD_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Attendance file exceeds the 10 MB limit",
        )

    if not file_name.lower().endswith(".xlsx"):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Only .xlsx attendance files are supported",
        )

    if class_id is None and uploaded_by.role != "SUPER_ADMIN":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A class is required for scoped attendance imports",
        )

    selected_class = None
    if class_id is not None:
        selected_class = get_class(db, class_id, uploaded_by)
        if selected_class is None or not selected_class.is_active:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Selected class does not exist or is inactive",
            )

    parsed = parse_attendance_workbook(BytesIO(file_content))
    period_dates = [
        attendance_date
        for row in parsed.rows
        for attendance_date in row.attendance_by_date
    ]
    period_start = min(period_dates) if period_dates else attendance_date
    period_end = max(period_dates) if period_dates else attendance_date

    import_batch = AttendanceImportBatch(
        file_name=file_name,
        file_type="xlsx",
        attendance_date=attendance_date,
        class_id=class_id,
        total_rows=parsed.total_rows,
        valid_rows=0,
        invalid_rows=parsed.invalid_rows,
        duplicate_rows=parsed.duplicate_rows,
        status="PROCESSING",
        uploaded_by=uploaded_by.id,
    )
    db.add(import_batch)
    db.flush()

    for row in parsed.rows:
        student_query = select(Student).where(
            Student.student_code == row.student_code,
        )
        if selected_class is not None:
            student_query = student_query.where(
                Student.class_id == selected_class.id,
            )

        student = db.execute(student_query).scalar_one_or_none()
        if student is None:
            import_batch.invalid_rows += 1
            continue

        import_batch.valid_rows += 1
        db.add(
            AttendanceSummary(
                student_id=student.id,
                import_batch_id=import_batch.id,
                attendance_percentage=row.college_percentage,
                period_start=period_start,
                period_end=period_end,
                source_type="COLLEGE_EXCEL",
                calculation_method="COLLEGE_PROVIDED_TOTAL",
            )
        )

        for row_date, raw_status in row.attendance_by_date.items():
            existing_record = db.execute(
                select(AttendanceRecord).where(
                    AttendanceRecord.student_id == student.id,
                    AttendanceRecord.attendance_date == row_date,
                )
            ).scalar_one_or_none()
            if existing_record is not None:
                import_batch.duplicate_rows += 1
                continue

            normalized_status = _normalize_attendance_status(raw_status)
            attendance = AttendanceRecord(
                student_id=student.id,
                attendance_date=row_date,
                status=normalized_status,
                source_type="EXCEL",
                source_reference=str(import_batch.id),
                import_batch_id=import_batch.id,
            )
            db.add(attendance)
            db.flush()

            if normalized_status == "ABSENT":
                db.add(
                    AbsenceEvent(
                        student_id=student.id,
                        attendance_record_id=attendance.id,
                        absence_date=row_date,
                        status="PENDING",
                        eligible_for_call=True,
                    )
                )

    import_batch.status = "COMPLETED" if import_batch.valid_rows else "FAILED"
    db.commit()
    db.refresh(import_batch)
    return import_batch


def _normalize_attendance_status(raw_status: str) -> str:
    normalized = raw_status.strip().upper()
    if normalized == "P":
        return "PRESENT"
    if normalized == "A":
        return "ABSENT"
    return normalized


def find_student_by_code(
    db: Session,
    student_code: str,
) -> Student | None:

    result = db.execute(
        select(Student).where(
            Student.student_code == student_code
        )
    )

    return result.scalar_one_or_none()