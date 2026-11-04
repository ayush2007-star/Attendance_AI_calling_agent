from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from app.models.parent import Parent
from app.models.campaign import CallCampaign
from app.integrations.calling.base import CallRequest, CallingProvider
from app.models.call_attempt import CallAttempt
from app.models.campaign_target import CampaignTarget
from app.models.class_model import ClassModel
from app.models.student import Student
from app.models.user import User
from app.models.authorization import user_scopes


def queue_campaign_target(
    db: Session,
    campaign_target_id: UUID,
    current_user: User,
) -> CallAttempt:
    query = (
        select(CampaignTarget)
        .join(Student, Student.id == CampaignTarget.student_id)
        .join(ClassModel, ClassModel.id == Student.class_id)
        .where(CampaignTarget.id == campaign_target_id)
    )
    if current_user.role != "SUPER_ADMIN":
        query = query.join(
            user_scopes,
            user_scopes.c.scope_id == ClassModel.scope_id,
        ).where(user_scopes.c.user_id == current_user.id)

    target = db.execute(query).scalar_one_or_none()
    if target is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Campaign target not found",
        )

    if target.status not in {"PENDING", "FAILED"}:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Campaign target is not available for queueing",
        )

    if target.parent_id is None or not target.selected_phone_number:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Campaign target has no callable contact",
        )

    last_attempt_number = db.execute(
        select(func.max(CallAttempt.attempt_number)).where(
            CallAttempt.campaign_target_id == campaign_target_id,
        )
    ).scalar_one()

    attempt = CallAttempt(
        campaign_id=target.campaign_id,
        campaign_target_id=target.id,
        absence_event_id=None,
        parent_id=target.parent_id,
        attempt_number=(last_attempt_number or 0) + 1,
        phone_number=target.selected_phone_number,
        status="QUEUED",
    )
    target.status = "QUEUED"
    db.add(attempt)
    db.commit()
    db.refresh(attempt)
    return attempt

def get_campaign_target_context(
    db: Session,
    campaign_target_id: UUID,
    current_user: User,
):
    query = (
        select(
            CampaignTarget,
            Student,
            Parent,
            CallCampaign,
        )
        .join(Student, Student.id == CampaignTarget.student_id)
        .join(Parent, Parent.id == CampaignTarget.parent_id)
        .join(CallCampaign, CallCampaign.id == CampaignTarget.campaign_id)
        .join(ClassModel, ClassModel.id == Student.class_id)
        .where(CampaignTarget.id == campaign_target_id)
    )

    if current_user.role != "SUPER_ADMIN":
        query = query.join(
            user_scopes,
            user_scopes.c.scope_id == ClassModel.scope_id,
        ).where(
            user_scopes.c.user_id == current_user.id
        )

    result = db.execute(query).one_or_none()

    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Campaign target not found",
        )

    target, student, parent, campaign = result

    if not target.selected_phone_number:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Campaign target has no callable contact",
        )

    return {
        "campaign_target_id": target.id,
        "campaign_id": target.campaign_id,
        "student_id": student.id,
        "student_name": f"{student.first_name} {student.last_name or ''}".strip(),
        "student_code": student.student_code,
        "parent_id": parent.id,
        "parent_name": parent.name,
        "phone_number": target.selected_phone_number,
        "preferred_language": parent.preferred_language,
        "attendance_percentage": float(target.attendance_percentage_used),
        "threshold": float(target.threshold_used),
        "eligibility_reason": target.eligibility_reason,
        "attendance_date": campaign.attendance_date,
        "attendance_period_start": campaign.attendance_period_start,
        "attendance_period_end": campaign.attendance_period_end,
    }
def dispatch_call(
    db: Session,
    attempt_id: UUID,
    provider: CallingProvider,
) -> CallAttempt:
    attempt = db.get(CallAttempt, attempt_id)
    if attempt is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Call attempt not found",
        )

    if attempt.status != "QUEUED":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Call attempt is not queued",
        )

    result = provider.start_call(
        CallRequest(
            attempt_id=attempt.id,
            phone_number=attempt.phone_number,
            campaign_id=attempt.campaign_id,
        )
    )
    attempt.provider_call_id = result.provider_call_id
    attempt.status = result.status
    attempt.started_at = result.started_at or datetime.now(timezone.utc)
    db.commit()
    db.refresh(attempt)
    return attempt
