from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies import require_permission
from app.db.dependencies import get_db
from app.models.user import User
from app.schemas.scope import ScopeCreate, ScopeResponse
from app.services.scope_service import create_scope, get_scopes


router = APIRouter(prefix="/scopes", tags=["Organization"])


@router.get("", response_model=list[ScopeResponse])
def list_scopes(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("scopes.read")),
):
    return get_scopes(db, current_user)


@router.post(
    "",
    response_model=ScopeResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_scope_endpoint(
    data: ScopeCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("scopes.manage")),
):
    if current_user.role != "SUPER_ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the institution director can create departments",
        )
    try:
        return create_scope(db, data)
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(error),
        ) from error
