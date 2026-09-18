from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from datetime import date

from app.models.attendance_summary import AttendanceSummary
from app.models.campaign import CallCampaign
from app.models.campaign_target import CampaignTarget
from app.models.class_model import ClassModel
from app.models.parent import Parent
from app.models.student import Student
from app.models.student_parent import StudentParent
from app.models.system_setting import SystemSetting
from app.models.user import User
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

    eligible_summaries = _find_latest_eligible_summaries(
        db=db,
        campaign_date=data.attendance_date,
        threshold=threshold,
        class_id=selected_class.id if selected_class else None,
        is_super_admin=created_by.role == "SUPER_ADMIN",
    )

    campaign = CallCampaign(
        name=data.name,
        attendance_date=data.attendance_date,
        attendance_period_start=_period_start(eligible_summaries, data.attendance_date),
        attendance_period_end=_period_end(eligible_summaries, data.attendance_date),
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

    for summary, student in eligible_summaries:
        parent = _select_primary_parent(db, student.id)
        db.add(
            CampaignTarget(
                campaign_id=campaign.id,
                student_id=student.id,
                parent_id=parent.id if parent else None,
                attendance_percentage_used=summary.attendance_percentage,
                threshold_used=threshold,
                eligibility_reason=(
                    "BELOW_THRESHOLD"
                    if parent
                    else "BELOW_THRESHOLD_NO_CONTACT"
                ),
                status="PENDING",
                selected_phone_number=(
                    parent.primary_phone if parent else None
                ),
            )
        )

    campaign.total_targets = len(eligible_summaries)
    db.commit()
    db.refresh(campaign)
    return campaign


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


def _resolve_threshold(db: Session, requested_threshold: float | None) -> float:
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


def _find_latest_eligible_summaries(
    db: Session,
    campaign_date: date,
    threshold: float,
    class_id,
    is_super_admin: bool,
) -> list[tuple[AttendanceSummary, Student]]:
    query = (
        select(AttendanceSummary, Student)
        .join(Student, Student.id == AttendanceSummary.student_id)
        .join(ClassModel, ClassModel.id == Student.class_id)
        .where(
            AttendanceSummary.attendance_percentage < threshold,
            AttendanceSummary.period_end <= campaign_date,
        )
        .order_by(
            AttendanceSummary.student_id,
            AttendanceSummary.recorded_at.desc(),
        )
    )
    if class_id is not None:
        query = query.where(ClassModel.id == class_id)
    elif not is_super_admin:
        query = query.where(False)

    latest_by_student = {}
    for summary, student in db.execute(query).all():
        latest_by_student.setdefault(student.id, (summary, student))
    return list(latest_by_student.values())


def _select_primary_parent(db: Session, student_id):
    return db.execute(
        select(Parent)
        .join(StudentParent, StudentParent.parent_id == Parent.id)
        .where(
            StudentParent.student_id == student_id,
            StudentParent.is_primary.is_(True),
            Parent.is_active.is_(True),
        )
        .order_by(Parent.created_at)
    ).scalar_one_or_none()


def _period_start(
    summaries: list[tuple[AttendanceSummary, Student]],
    fallback: date,
) -> date:
    return min(
        (summary.period_start for summary, _ in summaries),
        default=fallback,
    )


def _period_end(
    summaries: list[tuple[AttendanceSummary, Student]],
    fallback: date,
) -> date:
    return max(
        (summary.period_end for summary, _ in summaries),
        default=fallback,
    )
from app.models.campaign import CallCampaign
from app.models.class_model import ClassModel
from app.models.user import User
from app.schemas.campaign import CampaignCreate
from app.services.class_service import get_class


def create_campaign(
    db: Session,
    data: CampaignCreate,
    created_by: User,
) -> CallCampaign:

    # Validate class if a class_id was provided
    if data.class_id is not None:
        class_obj = get_class(db, data.class_id, created_by)

        if class_obj is None or not class_obj.is_active:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Selected class does not exist or is inactive",
            )
    elif created_by.role != "SUPER_ADMIN":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A class is required for scoped campaigns",
        )

    campaign = CallCampaign(
        name=data.name,
        attendance_date=data.attendance_date,
        class_id=data.class_id,
        status="DRAFT",
        created_by=created_by.id,
        total_targets=0,
        completed_calls=0,
        failed_calls=0,
    )

    db.add(campaign)
    db.commit()
    db.refresh(campaign)

    return campaign