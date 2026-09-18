from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.attendance import AttendanceRecord
from app.models.absence import AbsenceEvent
from app.models.user import User
from app.schemas.attendance import AttendanceCreate
from app.services.student_service import get_student


def create_attendance(
    db: Session,
    data: AttendanceCreate,
    current_user: User,
) -> AttendanceRecord:
    get_student(db, data.student_id, current_user)

    attendance = AttendanceRecord(
        student_id=data.student_id,
        attendance_date=data.attendance_date,
        status=data.status,
        source_type=data.source_type,
        source_reference=data.source_reference,
        import_batch_id=data.import_batch_id,
    )

    db.add(attendance)
    db.flush()

    if data.status.upper() == "ABSENT":
        absence = AbsenceEvent(
            student_id=data.student_id,
            attendance_record_id=attendance.id,
            absence_date=data.attendance_date,
            status="PENDING",
            eligible_for_call=True,
        )

        db.add(absence)

    db.commit()
    db.refresh(attendance)

    return attendance