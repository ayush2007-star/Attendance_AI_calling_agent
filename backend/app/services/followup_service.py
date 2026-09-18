from datetime import datetime, timezone
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.followup import Followup
from app.models.user import User
from app.services.student_service import get_student
from app.services.rule_engine import validate_callback_decision


def schedule_followup(
    db: Session,
    student_id: UUID,
    reason: str,
    scheduled_for: datetime,
    timezone_name: str = "UTC",
    conversation_id: UUID | None = None,
    campaign_id: UUID | None = None,
    campaign_target_id: UUID | None = None,
    parent_id: UUID | None = None,
    assigned_to: UUID | None = None,
    priority: str = "MEDIUM",
    category: str = "OTHER",
    current_user: User | None = None,
) -> Followup:
    validate_callback_decision(category, True, scheduled_for)
    _validate_timezone(timezone_name)

    if current_user is not None:
        get_student(db, student_id, current_user)

    followup = Followup(
        student_id=student_id,
        conversation_id=conversation_id,
        campaign_id=campaign_id,
        campaign_target_id=campaign_target_id,
        parent_id=parent_id,
        assigned_to=assigned_to,
        reason=reason,
        priority=priority,
        status="SCHEDULED",
        due_at=scheduled_for,
        scheduled_for=scheduled_for,
        timezone_name=timezone_name,
        retry_count=0,
    )
    db.add(followup)
    db.commit()
    db.refresh(followup)
    return followup


def mark_due_followups(
    db: Session,
    now: datetime | None = None,
    limit: int = 100,
) -> list[Followup]:
    current_time = now or datetime.now(timezone.utc)
    if current_time.tzinfo is None or current_time.utcoffset() is None:
        raise ValueError("now must be timezone-aware")

    followups = db.execute(
        select(Followup)
        .where(
            Followup.status.in_(["PENDING", "SCHEDULED"]),
            Followup.scheduled_for.is_not(None),
            Followup.scheduled_for <= current_time,
        )
        .order_by(Followup.scheduled_for)
        .with_for_update(skip_locked=True)
        .limit(limit)
    ).scalars().all()

    for followup in followups:
        followup.status = "DUE"
    db.commit()
    return followups


def claim_due_followup(db: Session, followup_id: UUID) -> Followup:
    followup = db.get(Followup, followup_id)
    if followup is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Follow-up not found",
        )
    if followup.status != "DUE":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Follow-up is not due",
        )

    followup.status = "IN_PROGRESS"
    db.commit()
    db.refresh(followup)
    return followup


def complete_followup(db: Session, followup_id: UUID) -> Followup:
    return _set_terminal_status(db, followup_id, "COMPLETED")


def cancel_followup(db: Session, followup_id: UUID) -> Followup:
    return _set_terminal_status(db, followup_id, "CANCELLED")


def _set_terminal_status(
    db: Session,
    followup_id: UUID,
    status_value: str,
) -> Followup:
    followup = db.get(Followup, followup_id)
    if followup is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Follow-up not found",
        )
    if followup.status not in {"IN_PROGRESS", "DUE", "SCHEDULED"}:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Follow-up is not active",
        )

    followup.status = status_value
    followup.completed_at = (
        datetime.now(timezone.utc)
        if status_value == "COMPLETED"
        else None
    )
    db.commit()
    db.refresh(followup)
    return followup


def _validate_timezone(timezone_name: str) -> None:
    try:
        ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Unknown follow-up timezone",
        ) from exc
