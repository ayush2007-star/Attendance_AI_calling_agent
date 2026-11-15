from datetime import date, datetime, timezone
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.integrations.calling.factory import get_calling_provider
from app.models.attendance_summary import AttendanceSummary
from app.models.attendance import AttendanceRecord
from app.models.call_attempt import CallAttempt
from app.models.campaign import CallCampaign
from app.models.campaign_target import CampaignTarget
from app.models.class_model import ClassModel
from app.models.parent import Parent
from app.models.student import Student
from app.models.student_parent import StudentParent
from app.models.system_setting import SystemSetting
from app.models.user import User
from app.models.authorization import user_scopes
from app.schemas.campaign import CampaignCreate
from app.services.class_service import get_class


DEFAULT_THRESHOLD = 75.0


def create_campaign(
    db: Session,
    data: CampaignCreate,
    created_by: User,
) -> CallCampaign:
    selected_class = _validate_campaign_scope(db, data, created_by)
    threshold = _resolve_threshold(db, data.threshold)

    absent_students = _find_absent_students(
        db=db,
        campaign_date=data.attendance_date,
        class_id=selected_class.id if selected_class else None,
        is_super_admin=created_by.role == "SUPER_ADMIN",
    )
    latest_summaries = _find_latest_summaries(
        db=db,
        campaign_date=data.attendance_date,
        student_ids=[student.id for student in absent_students],
    )

    campaign = CallCampaign(
        name=data.name,
        attendance_date=data.attendance_date,
        attendance_period_start=data.attendance_date,
        attendance_period_end=data.attendance_date,
        threshold_used=threshold,
        class_id=data.class_id,
        status="DRAFT",
        created_by=created_by.id,
        total_targets=0,
        completed_calls=0,
        failed_calls=0,
    )

    db.add(campaign)
    db.flush()

    for student in absent_students:
        parent = _select_primary_parent(db, student.id)
        summary = latest_summaries.get(student.id)
        is_authorized = bool(parent and parent.call_consent and not parent.call_opt_out)

        db.add(
            CampaignTarget(
                campaign_id=campaign.id,
                student_id=student.id,
                parent_id=parent.id if parent else None,
                attendance_percentage_used=(
                    summary.attendance_percentage if summary else 0
                ),
                threshold_used=threshold,
                eligibility_reason=(
                    "ABSENT_ON_DATE"
                    if parent
                    else "ABSENT_ON_DATE_NO_CONTACT"
                ),
                status="PENDING",
                selected_phone_number=(
                    parent.primary_phone if parent else None
                ),
                contact_authorized=is_authorized,
            )
        )

    campaign.total_targets = len(absent_students)

    db.commit()
    db.refresh(campaign)

    return campaign


def get_campaign_targets(
    db: Session,
    campaign_id: UUID,
    current_user: User,
) -> list[dict]:
    campaign = db.get(CallCampaign, campaign_id)
    if campaign is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Campaign not found",
        )

    query = (
        select(CampaignTarget, Student, Parent)
        .join(Student, Student.id == CampaignTarget.student_id)
        .join(ClassModel, ClassModel.id == Student.class_id)
        .outerjoin(Parent, Parent.id == CampaignTarget.parent_id)
        .where(
            CampaignTarget.campaign_id == campaign_id,
            Student.is_active.is_(True),
            ClassModel.is_active.is_(True),
        )
        .order_by(Student.roll_number)
    )
    if current_user.role != "SUPER_ADMIN":
        query = query.join(
            user_scopes,
            user_scopes.c.scope_id == ClassModel.scope_id,
        ).where(user_scopes.c.user_id == current_user.id)

    return [
        {
            "id": target.id,
            "student_id": student.id,
            "student_code": student.student_code,
            "roll_number": student.roll_number,
            "student_name": f"{student.first_name} {student.last_name or ''}".strip(),
            "parent_name": parent.name if parent else None,
            "phone_number": target.selected_phone_number,
            "attendance_percentage": float(target.attendance_percentage_used),
            "threshold": float(target.threshold_used),
            "eligibility_reason": target.eligibility_reason,
            "status": target.status,
            "contact_authorized": getattr(target, "contact_authorized", True),
        }
        for target, student, parent in db.execute(query).all()
    ]


def list_campaigns(
    db: Session,
    current_user: User,
    limit: int = 50,
    offset: int = 0,
) -> list[CallCampaign]:
    query = select(CallCampaign).order_by(desc(CallCampaign.created_at))
    if current_user.role != "SUPER_ADMIN":
        query = (
            query.outerjoin(ClassModel, ClassModel.id == CallCampaign.class_id)
            .join(user_scopes, user_scopes.c.scope_id == ClassModel.scope_id)
            .where(user_scopes.c.user_id == current_user.id)
        )
    return list(db.execute(query.offset(offset).limit(limit)).scalars().all())


def get_campaign(
    db: Session,
    campaign_id: UUID,
    current_user: User,
) -> CallCampaign:
    campaign = db.get(CallCampaign, campaign_id)
    if campaign is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Campaign not found",
        )
    if current_user.role != "SUPER_ADMIN" and campaign.class_id:
        scoped = db.execute(
            select(CallCampaign.id)
            .join(ClassModel, ClassModel.id == CallCampaign.class_id)
            .join(user_scopes, user_scopes.c.scope_id == ClassModel.scope_id)
            .where(
                CallCampaign.id == campaign_id,
                user_scopes.c.user_id == current_user.id,
            )
        ).scalar_one_or_none()
        if not scoped:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have access to this campaign scope",
            )
    return campaign


def start_campaign(
    db: Session,
    campaign_id: UUID,
    current_user: User,
) -> CallCampaign:
    campaign = get_campaign(db, campaign_id, current_user)
    if campaign.status in ("COMPLETED", "STOPPED"):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Campaign is already {campaign.status.lower()}",
        )

    campaign.status = "RUNNING"
    if not campaign.started_at:
        campaign.started_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(campaign)
    return campaign


def pause_campaign(
    db: Session,
    campaign_id: UUID,
    current_user: User,
) -> CallCampaign:
    campaign = get_campaign(db, campaign_id, current_user)
    campaign.status = "PAUSED"
    db.commit()
    db.refresh(campaign)
    return campaign


def stop_campaign(
    db: Session,
    campaign_id: UUID,
    current_user: User,
) -> CallCampaign:
    campaign = get_campaign(db, campaign_id, current_user)
    campaign.status = "COMPLETED"
    campaign.completed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(campaign)
    return campaign


def dispatch_next_campaign_target(
    db: Session,
    campaign_id: UUID,
    current_user: User,
) -> dict:
    from app.services.calling_service import (
        dispatch_call,
        queue_campaign_target,
        simulate_completed_call,
    )

    campaign = get_campaign(db, campaign_id, current_user)

    # 1. Look for already queued target
    queued_target = db.execute(
        select(CampaignTarget)
        .where(
            CampaignTarget.campaign_id == campaign_id,
            CampaignTarget.status == "QUEUED",
        )
        .order_by(CampaignTarget.created_at)
        .limit(1)
    ).scalar_one_or_none()

    target_to_dispatch = queued_target

    # 2. If no target queued, find first PENDING target with valid contact
    if target_to_dispatch is None:
        pending_target = db.execute(
            select(CampaignTarget)
            .where(
                CampaignTarget.campaign_id == campaign_id,
                CampaignTarget.status == "PENDING",
                CampaignTarget.selected_phone_number.is_not(None),
                CampaignTarget.contact_authorized.is_(True),
            )
            .order_by(CampaignTarget.created_at)
            .limit(1)
        ).scalar_one_or_none()

        if pending_target is None:
            # Mark any uncontactable/unauthorized pending targets as SKIPPED
            uncontactable = db.execute(
                select(CampaignTarget).where(
                    CampaignTarget.campaign_id == campaign_id,
                    CampaignTarget.status == "PENDING",
                )
            ).scalars().all()
            for t in uncontactable:
                t.status = "SKIPPED"
            if uncontactable:
                db.commit()

            # Check if all completed
            remaining = db.execute(
                select(func.count(CampaignTarget.id)).where(
                    CampaignTarget.campaign_id == campaign_id,
                    CampaignTarget.status.in_(["PENDING", "QUEUED"]),
                )
            ).scalar() or 0
            if remaining == 0 and campaign.status == "RUNNING":
                campaign.status = "COMPLETED"
                campaign.completed_at = datetime.now(timezone.utc)
                db.commit()
            return {
                "message": "No more eligible targets pending call dispatch in this campaign",
                "campaign_id": campaign.id,
                "completed": True,
            }

        # Queue the pending target
        queue_campaign_target(db, pending_target.id, current_user)
        target_to_dispatch = pending_target

    # 3. Find the queued CallAttempt for this target
    attempt = db.execute(
        select(CallAttempt)
        .where(
            CallAttempt.campaign_target_id == target_to_dispatch.id,
            CallAttempt.status == "QUEUED",
        )
        .order_by(desc(CallAttempt.created_at))
        .limit(1)
    ).scalar_one_or_none()

    if attempt is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No queued call attempt found for target",
        )

    # 4. Dispatch call
    provider = get_calling_provider()
    dispatched_attempt = dispatch_call(db, attempt.id, provider, current_user)

    # If running in mock/demo mode, complete the simulated call immediately so results reflect in UI
    if not settings.real_calls_enabled:
        dispatched_attempt = simulate_completed_call(
            db=db,
            attempt_id=dispatched_attempt.id,
            current_user=current_user,
            reason_preset="MEDICAL_REASON",
        )

    return {
        "message": "Call successfully dispatched",
        "attempt_id": dispatched_attempt.id,
        "provider_call_id": dispatched_attempt.provider_call_id,
        "status": dispatched_attempt.status,
        "target_id": target_to_dispatch.id,
        "phone_number": dispatched_attempt.phone_number,
        "is_demo": not settings.real_calls_enabled,
    }



def _validate_campaign_scope(
    db: Session,
    data: CampaignCreate,
    created_by: User,
) -> ClassModel | None:
    if data.class_id is not None:
        selected_class = get_class(db, data.class_id, created_by)

        if selected_class is None or not selected_class.is_active:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Selected class does not exist or is inactive",
            )

        return selected_class

    if created_by.role != "SUPER_ADMIN":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A class is required for scoped campaigns",
        )

    return None


def _resolve_threshold(
    db: Session,
    requested_threshold: float | None,
) -> float:
    if requested_threshold is not None:
        return requested_threshold

    configured_value = db.execute(
        select(SystemSetting.value).where(
            SystemSetting.key == "attendance_threshold_default"
        )
    ).scalar_one_or_none()

    if configured_value is None:
        return DEFAULT_THRESHOLD

    try:
        threshold = float(configured_value)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Configured attendance threshold is invalid",
        ) from exc

    if not 0 <= threshold <= 100:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Configured attendance threshold is out of range",
        )

    return threshold


def _find_absent_students(
    db: Session,
    campaign_date: date,
    class_id: UUID | None,
    is_super_admin: bool,
) -> list[Student]:
    query = (
        select(Student)
        .join(
            AttendanceRecord,
            AttendanceRecord.student_id == Student.id,
        )
        .join(
            ClassModel,
            ClassModel.id == Student.class_id,
        )
        .where(
            AttendanceRecord.attendance_date == campaign_date,
            AttendanceRecord.status == "ABSENT",
            Student.is_active.is_(True),
            ClassModel.is_active.is_(True),
        )
        .order_by(Student.roll_number)
    )

    if class_id is not None:
        query = query.where(ClassModel.id == class_id)
    elif not is_super_admin:
        query = query.where(False)

    return list(db.scalars(query).unique().all())


def _find_latest_summaries(
    db: Session,
    campaign_date: date,
    student_ids: list[UUID],
) -> dict[UUID, AttendanceSummary]:
    if not student_ids:
        return {}

    query = (
        select(AttendanceSummary)
        .where(
            AttendanceSummary.student_id.in_(student_ids),
            AttendanceSummary.period_end <= campaign_date,
        )
        .order_by(
            AttendanceSummary.student_id,
            AttendanceSummary.recorded_at.desc(),
        )
    )

    latest_by_student: dict[UUID, AttendanceSummary] = {}
    for summary in db.scalars(query).all():
        latest_by_student.setdefault(summary.student_id, summary)
    return latest_by_student


def _select_primary_parent(
    db: Session,
    student_id: UUID,
) -> Parent | None:
    return db.execute(
        select(Parent)
        .join(
            StudentParent,
            StudentParent.parent_id == Parent.id,
        )
        .where(
            StudentParent.student_id == student_id,
            StudentParent.is_primary.is_(True),
            Parent.is_active.is_(True),
        )
        .order_by(Parent.created_at)
    ).scalars().first()
