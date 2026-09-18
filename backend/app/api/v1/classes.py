from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.dependencies import require_permission
from app.db.dependencies import get_db
from app.models.user import User
from app.schemas.class_schema import ClassCreate, ClassResponse
from app.services.class_service import (
    create_class as create_class_service,
    get_class as get_class_service,
    get_classes as get_classes_service,
)


router = APIRouter(
    prefix="/classes",
    tags=["Classes"],
)


@router.post(
    "",
    response_model=ClassResponse,
)
def create_class(
    data: ClassCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("class.create")),
):
    return create_class_service(db, data, current_user)


@router.get(
    "",
    response_model=list[ClassResponse],
)
def get_classes(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("class.read")),
):
    return get_classes_service(db, current_user)


@router.get(
    "/{class_id}",
    response_model=ClassResponse,
)
def get_class(
    class_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("class.read")),
):
    class_obj = get_class_service(db, class_id, current_user)

    if class_obj is None:
        raise HTTPException(
            status_code=404,
            detail="Class not found",
        )

    return class_obj