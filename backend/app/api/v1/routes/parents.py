from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.db.dependencies import get_db
from app.schemas.parent import ParentCreate, ParentResponse
from app.services.parent_service import create_parent


router = APIRouter(
    prefix="/parents",
    tags=["Parents"],
)


@router.post(
    "",
    response_model=ParentResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_parent_endpoint(
    data: ParentCreate,
    db: Session = Depends(get_db),
):
    return create_parent(db, data)