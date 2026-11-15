from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.dependencies import require_permission
from app.db.dependencies import get_db
from app.models.user import User
from app.schemas.campaign import (
    CampaignCreate,
    CampaignResponse,
    CampaignTargetResponse,
)
from app.services.campaign_service import (
    create_campaign,
    dispatch_next_campaign_target,
    get_campaign,
    get_campaign_targets,
    list_campaigns,
    pause_campaign,
    start_campaign,
    stop_campaign,
)

router = APIRouter(
    prefix="/campaigns",
    tags=["Call Campaigns"],
)


@router.get(
    "",
    response_model=list[CampaignResponse],
)
def list_campaigns_endpoint(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("calls.read")),
):
    """List attendance call campaigns with counts and status."""
    return list_campaigns(db, current_user, limit=limit, offset=offset)


@router.post(
    "",
    response_model=CampaignResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_campaign_endpoint(
    data: CampaignCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_permission("campaign.create")
    ),
):
    """Create a new call campaign snapshot for absent students on a given date."""
    try:
        return create_campaign(
            db=db,
            data=data,
            created_by=current_user,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )


@router.get(
    "/{campaign_id}",
    response_model=CampaignResponse,
)
def get_campaign_endpoint(
    campaign_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("calls.read")),
):
    """Get single campaign details and progress counters."""
    return get_campaign(db, campaign_id, current_user)


@router.get(
    "/{campaign_id}/targets",
    response_model=list[CampaignTargetResponse],
)
def list_campaign_targets(
    campaign_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("calls.read")),
):
    """List eligible absent student targets for a campaign with guardian contact info."""
    return get_campaign_targets(db, campaign_id, current_user)


@router.post(
    "/{campaign_id}/start",
    response_model=CampaignResponse,
)
def start_campaign_endpoint(
    campaign_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("calls.manage")),
):
    """Start an approved campaign for controlled sequential call dispatch."""
    return start_campaign(db, campaign_id, current_user)


@router.post(
    "/{campaign_id}/pause",
    response_model=CampaignResponse,
)
def pause_campaign_endpoint(
    campaign_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("calls.manage")),
):
    """Pause active calling on this campaign."""
    return pause_campaign(db, campaign_id, current_user)


@router.post(
    "/{campaign_id}/stop",
    response_model=CampaignResponse,
)
def stop_campaign_endpoint(
    campaign_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("calls.manage")),
):
    """Stop and complete this campaign."""
    return stop_campaign(db, campaign_id, current_user)


@router.post(
    "/{campaign_id}/dispatch-next",
    response_model=dict[str, Any],
)
def dispatch_next_target_endpoint(
    campaign_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("calls.manage")),
):
    """Controlled sequential dispatch of the next eligible absent student call."""
    return dispatch_next_campaign_target(db, campaign_id, current_user)
