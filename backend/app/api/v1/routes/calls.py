from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.dependencies import require_permission
from app.db.dependencies import get_db
from app.models.user import User
from app.schemas.calling import CallAttemptResponse
from app.services.calling_service import queue_campaign_target


router = APIRouter(
    prefix="/calls",
    tags=["Calls"],
)


@router.post(
    "/targets/{campaign_target_id}/queue",
    response_model=CallAttemptResponse,
    status_code=status.HTTP_201_CREATED,
)
def queue_call(
    campaign_target_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("calls.manage")),
):
    return queue_campaign_target(db, campaign_target_id, current_user)
