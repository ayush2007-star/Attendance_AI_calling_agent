from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.absence import AbsenceEvent
from app.models.attendance import AttendanceRecord
from app.models.user import User
from app.schemas.absence import AbsenceCreate
from app.services.student_service import get_student


def create_absence(
    db: Session,
    data: AbsenceCreate,
    current_user: User,
) -> AbsenceEvent:
    get_student(db, data.student_id, current_user)
    attendance = db.get(AttendanceRecord, data.attendance_record_id)
    if attendance is None or attendance.student_id != data.student_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Attendance record not found for this student",
        )

    absence = AbsenceEvent(
        student_id=data.student_id,
        attendance_record_id=data.attendance_record_id,
        absence_date=data.absence_date,
        status=data.status,
        eligible_for_call=data.eligible_for_call,
    )

    db.add(absence)
    db.commit()
    db.refresh(absence)

    return absence