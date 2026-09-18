from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.dependencies import require_permission
from app.db.dependencies import get_db
from app.models.user import User
from app.schemas.followup import FollowupCreate, FollowupResponse
from app.services.followup_service import schedule_followup


router = APIRouter(
    prefix="/followups",
    tags=["Follow-ups"],
)


@router.post(
    "",
    response_model=FollowupResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_followup(
    data: FollowupCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("followup.manage")),
):
    return schedule_followup(
        db=db,
        student_id=data.student_id,
        reason=data.reason,
        scheduled_for=data.scheduled_for,
        timezone_name=data.timezone_name,
        conversation_id=data.conversation_id,
        campaign_id=data.campaign_id,
        campaign_target_id=data.campaign_target_id,
        parent_id=data.parent_id,
        assigned_to=data.assigned_to,
        priority=data.priority,
        category=data.category,
        current_user=current_user,
    )
