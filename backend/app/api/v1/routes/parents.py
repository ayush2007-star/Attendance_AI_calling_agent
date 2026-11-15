from uuid import UUID
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.dependencies import require_permission
from app.db.dependencies import get_db
from app.models.user import User
from app.schemas.parent import ParentCreate, ParentResponse, ParentUpdate
from app.services.parent_service import (
    create_parent,
    get_parent,
    list_parents,
    update_parent,
)

router = APIRouter(
    prefix="/parents",
    tags=["Parents & Guardians"],
)


@router.get(
    "",
    response_model=list[ParentResponse],
)
def list_parents_endpoint(
    search: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("student.read")),
):
    """List parents and guardians with contact details and consent status."""
    return list_parents(db, search=search, limit=limit, offset=offset)


@router.get(
    "/{parent_id}",
    response_model=ParentResponse,
)
def get_parent_endpoint(
    parent_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("student.read")),
):
    """Retrieve parent/guardian contact information and preferences."""
    return get_parent(db, parent_id)


@router.post(
    "",
    response_model=ParentResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_parent_endpoint(
    data: ParentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("student.create")),
):
    """Create a parent/guardian record."""
    return create_parent(db, data)


@router.patch(
    "/{parent_id}",
    response_model=ParentResponse,
)
def update_parent_endpoint(
    parent_id: UUID,
    data: ParentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("student.manage")),
):
    """Update parent details, phone number, or calling consent/opt-out status."""
    return update_parent(db, parent_id, data)
