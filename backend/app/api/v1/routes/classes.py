from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies import require_permission
from app.db.dependencies import get_db
from app.models.user import User
from app.schemas.class_schema import ClassCreate, ClassResponse
from app.services.class_service import (
    create_class,
    get_class,
    get_classes,
)

router = APIRouter(
    prefix="/classes",
    tags=["Classes"],
)


@router.post(
    "",
    response_model=ClassResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_class_endpoint(
    data: ClassCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("class.create")),
):
    return create_class(db, data, current_user)


@router.get(
    "",
    response_model=list[ClassResponse],
)
def list_classes(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("class.read")),
):
    return get_classes(db, current_user)


@router.get(
    "/{class_id}",
    response_model=ClassResponse,
)
def get_class_endpoint(
    class_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("class.read")),
):
    class_obj = get_class(db, class_id, current_user)

    if class_obj is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Class not found",
        )

    return class_obj