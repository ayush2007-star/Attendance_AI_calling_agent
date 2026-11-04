from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.dependencies import require_permission
from app.db.dependencies import get_db
from app.models.user import User
from app.schemas.calling import CallAttemptResponse, CallContextResponse
from app.services.calling_service import (
    dispatch_call,
    get_campaign_target_context,
    queue_campaign_target,
)
from app.integrations.calling.local import LocalCallingProvider
from app.schemas.calling import (
    CallAttemptResponse,
    CallContextResponse,
    CallStatusUpdate,
)
from app.services.conversation_service import update_call_status

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


@router.get(
    "/targets/{campaign_target_id}/context",
    response_model=CallContextResponse,
)
def get_call_context(
    campaign_target_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("calls.read")),
):
    return get_campaign_target_context(
        db,
        campaign_target_id,
        current_user,
    )


@router.post(
    "/attempts/{attempt_id}/dispatch",
    response_model=CallAttemptResponse,
)
def dispatch_call_attempt(
    attempt_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("calls.manage")),
):
    provider = LocalCallingProvider()
    return dispatch_call(db, attempt_id, provider)
@router.post(
    "/attempts/{provider_call_id}/status",
    response_model=CallAttemptResponse,
)
def update_provider_call_status(
    provider_call_id: str,
    data: CallStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("calls.manage")),
):
    return update_call_status(
        db,
        provider_call_id,
        data.status,
    )