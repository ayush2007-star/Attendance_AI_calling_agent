from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies import (
    require_permission,
)
from app.db.dependencies import get_db
from app.models.user import User
from app.schemas.campaign import CampaignCreate, CampaignResponse
from app.services.campaign_service import create_campaign


router = APIRouter(
    prefix="/campaigns",
    tags=["Call Campaigns"],
)


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