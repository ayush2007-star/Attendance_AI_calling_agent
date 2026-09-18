from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.call_attempt import CallAttempt
from app.models.campaign import CallCampaign
from app.models.campaign_target import CampaignTarget
from app.models.class_model import ClassModel
from app.models.followup import Followup
from app.models.student import Student
from app.models.user import User
from app.models.authorization import user_scopes
from app.schemas.dashboard import DashboardSummary


def get_dashboard_summary(
    db: Session,
    current_user: User,
) -> DashboardSummary:
    students_query = select(func.count(Student.id)).join(
        ClassModel,
        ClassModel.id == Student.class_id,
    )
    targets_query = select(func.count(CampaignTarget.id)).join(
        Student,
        Student.id == CampaignTarget.student_id,
    ).join(
        ClassModel,
        ClassModel.id == Student.class_id,
    )
    followups_query = select(func.count(Followup.id)).join(
        Student,
        Student.id == Followup.student_id,
    ).join(
        ClassModel,
        ClassModel.id == Student.class_id,
    )

    if current_user.role != "SUPER_ADMIN":
        students_query = students_query.join(
            user_scopes,
            user_scopes.c.scope_id == ClassModel.scope_id,
        ).where(user_scopes.c.user_id == current_user.id)
        targets_query = targets_query.join(
            user_scopes,
            user_scopes.c.scope_id == ClassModel.scope_id,
        ).where(user_scopes.c.user_id == current_user.id)
        followups_query = followups_query.join(
            user_scopes,
            user_scopes.c.scope_id == ClassModel.scope_id,
        ).where(user_scopes.c.user_id == current_user.id)

    campaign_query = select(func.count(CallCampaign.id)).select_from(CallCampaign)
    call_query = select(func.count(CallAttempt.id)).join(
        CallCampaign,
        CallCampaign.id == CallAttempt.campaign_id,
    )
    if current_user.role != "SUPER_ADMIN":
        campaign_query = campaign_query.join(
            ClassModel,
            ClassModel.id == CallCampaign.class_id,
        ).join(
            user_scopes,
            user_scopes.c.scope_id == ClassModel.scope_id,
        ).where(user_scopes.c.user_id == current_user.id)
        call_query = call_query.join(
            ClassModel,
            ClassModel.id == CallCampaign.class_id,
        ).join(
            user_scopes,
            user_scopes.c.scope_id == ClassModel.scope_id,
        ).where(user_scopes.c.user_id == current_user.id)

    active_campaigns = campaign_query.where(
        CallCampaign.status.in_(["READY", "RUNNING", "PAUSED"])
    )
    completed_calls = call_query.where(CallAttempt.status == "COMPLETED")
    failed_calls = call_query.where(CallAttempt.status == "FAILED")
    unanswered_calls = call_query.where(
        CallAttempt.status.in_(["NO_ANSWER", "BUSY"])
    )

    return DashboardSummary(
        students=db.scalar(students_query) or 0,
        eligible_targets=db.scalar(
            targets_query.where(CampaignTarget.status.not_in(["CANCELLED", "SKIPPED"]))
        ) or 0,
        active_campaigns=db.scalar(active_campaigns) or 0,
        completed_calls=db.scalar(completed_calls) or 0,
        failed_calls=db.scalar(failed_calls) or 0,
        unanswered_calls=db.scalar(unanswered_calls) or 0,
        pending_followups=db.scalar(
            followups_query.where(Followup.status == "PENDING")
        ) or 0,
        due_followups=db.scalar(
            followups_query.where(Followup.status == "DUE")
        ) or 0,
        scheduled_followups=db.scalar(
            followups_query.where(Followup.status == "SCHEDULED")
        ) or 0,
    )
