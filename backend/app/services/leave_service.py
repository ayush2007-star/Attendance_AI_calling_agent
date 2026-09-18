from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.authorization import user_scopes
from app.models.class_model import ClassModel
from app.models.leave import LeaveRecord
from app.models.student import Student
from app.models.user import User
from app.schemas.leave import LeaveCreate
from app.services.student_service import get_student


ALLOWED_TRANSITIONS = {
    "PENDING": {"APPROVED", "REJECTED", "CANCELLED"},
    "APPROVED": {"CANCELLED"},
    "REJECTED": set(),
    "CANCELLED": set(),
}


def create_leave(
    db: Session,
    data: LeaveCreate,
    current_user: User,
) -> LeaveRecord:
    get_student(db, data.student_id, current_user)
    leave = LeaveRecord(
        student_id=data.student_id,
        start_date=data.start_date,
        end_date=data.end_date,
        reason=data.reason,
        source=data.source,
        notes=data.notes,
        status="PENDING",
    )
    db.add(leave)
    db.commit()
    db.refresh(leave)
    return leave


def list_leaves(db: Session, current_user: User) -> list[LeaveRecord]:
    query = (
        select(LeaveRecord)
        .join(Student, Student.id == LeaveRecord.student_id)
        .join(ClassModel, ClassModel.id == Student.class_id)
        .order_by(LeaveRecord.start_date.desc())
    )
    if current_user.role != "SUPER_ADMIN":
        query = query.join(
            user_scopes,
            user_scopes.c.scope_id == ClassModel.scope_id,
        ).where(user_scopes.c.user_id == current_user.id)
    return list(db.execute(query).scalars().all())


def transition_leave(
    db: Session,
    leave_id: UUID,
    new_status: str,
    current_user: User,
) -> LeaveRecord:
    leave = db.get(LeaveRecord, leave_id)
    if leave is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Leave record not found",
        )

    get_student(db, leave.student_id, current_user)
    normalized_status = new_status.upper()
    allowed_statuses = ALLOWED_TRANSITIONS.get(leave.status, set())
    if normalized_status not in allowed_statuses:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Invalid leave status transition",
        )

    leave.status = normalized_status
    if normalized_status == "APPROVED":
        leave.approved_by = current_user.id
        leave.approved_at = datetime.now(timezone.utc)
    elif normalized_status in {"REJECTED", "CANCELLED"}:
        leave.approved_by = None
        leave.approved_at = None

    db.commit()
    db.refresh(leave)
    return leave
