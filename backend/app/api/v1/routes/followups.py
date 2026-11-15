from uuid import UUID
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.dependencies import require_permission
from app.db.dependencies import get_db
from app.models.user import User
from app.schemas.followup import (
    FollowupCreate,
    FollowupResponse,
    FollowupStatusUpdate,
)
from app.services.followup_service import (
    list_followups,
    schedule_followup,
    update_followup_status,
)

router = APIRouter(
    prefix="/followups",
    tags=["Follow-ups"],
)


@router.get(
    "",
    response_model=list[FollowupResponse],
)
def list_followups_endpoint(
    status: str | None = Query(default=None),
    priority: str | None = Query(default=None),
    student_id: UUID | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("followup.read")),
):
    """List parent follow-ups resulting from calls or absence reviews."""
    return list_followups(
        db=db,
        current_user=current_user,
        status_filter=status,
        priority_filter=priority,
        student_id=student_id,
        limit=limit,
        offset=offset,
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
    """Schedule a manual follow-up action for a student/parent."""
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


@router.patch(
    "/{followup_id}/status",
    response_model=FollowupResponse,
)
def update_status(
    followup_id: UUID,
    data: FollowupStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("followup.manage")),
):
    """Update follow-up status (e.g., mark COMPLETED, CANCELLED, or IN_PROGRESS)."""
    return update_followup_status(
        db=db,
        followup_id=followup_id,
        new_status=data.status,
        current_user=current_user,
    )
