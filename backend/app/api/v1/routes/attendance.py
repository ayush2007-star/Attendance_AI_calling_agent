from datetime import date
from typing import Any
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.api.dependencies import require_permission
from app.db.dependencies import get_db
from app.models.absence import AbsenceEvent
from app.models.attendance import AttendanceRecord
from app.models.class_model import ClassModel
from app.models.student import Student
from app.models.user import User
from app.models.authorization import user_scopes
from app.schemas.attendance import (
    AttendanceCreate,
    AttendanceResponse,
    BulkAttendanceCreate,
    QuickToggleRequest,
)
from app.services.attendance_service import create_attendance
from app.services.class_service import get_class
from app.services.student_service import get_student

router = APIRouter(
    prefix="/attendance",
    tags=["Attendance"],
)


@router.get("")
def list_attendance(
    class_id: UUID | None = None,
    attendance_date: date | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("attendance.read")),
) -> list[dict[str, Any]]:
    """Get attendance records for a class on a specific date, merging student details."""
    query_date = attendance_date or date.today()

    students_query = select(Student).where(Student.is_active.is_(True))
    if class_id:
        if get_class(db, class_id, current_user) is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Selected class does not exist or is outside your scope",
            )
        students_query = students_query.where(Student.class_id == class_id)
    elif current_user.role != "SUPER_ADMIN":
        students_query = students_query.join(
            ClassModel,
            ClassModel.id == Student.class_id,
        ).join(
            user_scopes,
            user_scopes.c.scope_id == ClassModel.scope_id,
        ).where(user_scopes.c.user_id == current_user.id)
    students_query = students_query.order_by(Student.roll_number)

    students = db.execute(students_query).scalars().all()

    student_ids = [s.id for s in students]
    records = db.execute(
        select(AttendanceRecord).where(
            AttendanceRecord.student_id.in_(student_ids),
            AttendanceRecord.attendance_date == query_date,
        )
    ).scalars().all()

    record_map = {r.student_id: r for r in records}

    results = []
    for s in students:
        rec = record_map.get(s.id)
        results.append({
            "student_id": str(s.id),
            "student_code": s.student_code,
            "roll_number": s.roll_number,
            "student_name": f"{s.first_name} {s.last_name or ''}".strip(),
            "class_id": str(s.class_id),
            "attendance_date": str(query_date),
            "status": rec.status if rec else "NOT_MARKED",
            "attendance_record_id": str(rec.id) if rec else None,
            "source_type": rec.source_type if rec else None,
        })
    return results


@router.post(
    "",
    response_model=AttendanceResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_attendance_endpoint(
    data: AttendanceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("attendance.create")),
):
    return create_attendance(db, data, current_user)


@router.post("/bulk", status_code=status.HTTP_200_OK)
def save_bulk_attendance(
    data: BulkAttendanceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("attendance.create")),
) -> dict[str, Any]:
    """Bulk update attendance for an entire class on a given date."""
    selected_class = get_class(db, data.class_id, current_user)
    if selected_class is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Selected class does not exist or is outside your scope",
        )

    students = [
        get_student(db, item.student_id, current_user)
        for item in data.records
    ]
    if any(student.class_id != selected_class.id for student in students):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Every attendance record must belong to the selected class",
        )

    saved_count = 0
    absent_count = 0

    for item in data.records:
        rec = db.execute(
            select(AttendanceRecord).where(
                AttendanceRecord.student_id == item.student_id,
                AttendanceRecord.attendance_date == data.attendance_date,
            )
        ).scalars().first()

        if not rec:
            rec = AttendanceRecord(
                id=uuid4(),
                student_id=item.student_id,
                attendance_date=data.attendance_date,
                status=item.status,
                source_type="ROLL_CALL_TERMINAL",
                source_reference=data.source_reference,
            )
            db.add(rec)
            db.flush()
        else:
            rec.status = item.status
            rec.source_type = "ROLL_CALL_TERMINAL"
            rec.source_reference = data.source_reference

        if item.status == "ABSENT":
            absent_count += 1
            absence = db.execute(
                select(AbsenceEvent).where(
                    AbsenceEvent.student_id == item.student_id,
                    AbsenceEvent.absence_date == data.attendance_date,
                )
            ).scalars().first()
            if not absence:
                absence = AbsenceEvent(
                    id=uuid4(),
                    student_id=item.student_id,
                    attendance_record_id=rec.id,
                    absence_date=data.attendance_date,
                    status="PENDING",
                    eligible_for_call=True,
                )
                db.add(absence)
        else:
            absence = db.execute(
                select(AbsenceEvent).where(
                    AbsenceEvent.student_id == item.student_id,
                    AbsenceEvent.absence_date == data.attendance_date,
                )
            ).scalar_one_or_none()
            if absence is not None:
                absence.status = "CANCELLED"
                absence.eligible_for_call = False

        saved_count += 1

    db.commit()
    return {
        "success": True,
        "class_id": str(data.class_id),
        "date": str(data.attendance_date),
        "total_marked": saved_count,
        "absent_count": absent_count,
        "message": f"Successfully updated attendance for {saved_count} students.",
    }


@router.post("/quick-toggle", status_code=status.HTTP_200_OK)
def quick_toggle_attendance(
    data: QuickToggleRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("attendance.create")),
) -> dict[str, Any]:
    """Instantly toggle single student attendance status in terminal."""
    get_student(db, data.student_id, current_user)

    rec = db.execute(
        select(AttendanceRecord).where(
            AttendanceRecord.student_id == data.student_id,
            AttendanceRecord.attendance_date == data.attendance_date,
        )
    ).scalars().first()

    if not rec:
        rec = AttendanceRecord(
            id=uuid4(),
            student_id=data.student_id,
            attendance_date=data.attendance_date,
            status=data.new_status,
            source_type="QUICK_TOGGLE",
            source_reference="1-Tap Terminal",
        )
        db.add(rec)
        db.flush()
    else:
        rec.status = data.new_status

    if data.new_status == "ABSENT":
        absence = db.execute(
            select(AbsenceEvent).where(
                AbsenceEvent.student_id == data.student_id,
                AbsenceEvent.absence_date == data.attendance_date,
            )
        ).scalars().first()
        if not absence:
            absence = AbsenceEvent(
                id=uuid4(),
                student_id=data.student_id,
                attendance_record_id=rec.id,
                absence_date=data.attendance_date,
                status="PENDING",
                eligible_for_call=True,
            )
            db.add(absence)
    else:
        absence = db.execute(
            select(AbsenceEvent).where(
                AbsenceEvent.student_id == data.student_id,
                AbsenceEvent.absence_date == data.attendance_date,
            )
        ).scalar_one_or_none()
        if absence is not None:
            absence.status = "CANCELLED"
            absence.eligible_for_call = False

    db.commit()
    return {
        "student_id": str(data.student_id),
        "date": str(data.attendance_date),
        "status": data.new_status,
    }
