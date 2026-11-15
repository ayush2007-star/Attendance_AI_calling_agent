from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies import require_permission
from app.db.dependencies import get_db
from app.models.user import User
from app.schemas.user import (
    UserCreate,
    UserCreatedResponse,
    UserResponse,
    UserStatusUpdate,
)
from app.services.user_service import (
    create_user,
    get_users,
    reset_user_password,
    set_user_active,
)


router = APIRouter(prefix="/users", tags=["User Management"])


def _convert_service_error(error: Exception) -> HTTPException:
    if isinstance(error, PermissionError):
        return HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(error),
        )
    if isinstance(error, LookupError):
        return HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        )
    return HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=str(error),
    )


@router.get("", response_model=list[UserResponse])
def list_users(
    db: Session = Depends(get_db),
    manager: User = Depends(require_permission("users.read")),
):
    try:
        return get_users(db, manager)
    except (PermissionError, LookupError, ValueError) as error:
        raise _convert_service_error(error) from error


@router.post(
    "",
    response_model=UserCreatedResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_user_endpoint(
    data: UserCreate,
    db: Session = Depends(get_db),
    manager: User = Depends(require_permission("users.manage")),
):
    try:
        user, temporary_password = create_user(db, data, manager)
    except (PermissionError, LookupError, ValueError) as error:
        raise _convert_service_error(error) from error
    return UserCreatedResponse(
        **UserResponse.model_validate(user).model_dump(),
        temporary_password=temporary_password,
    )


@router.patch("/{user_id}", response_model=UserResponse)
def update_user_status(
    user_id: UUID,
    data: UserStatusUpdate,
    db: Session = Depends(get_db),
    manager: User = Depends(require_permission("users.manage")),
):
    try:
        return set_user_active(db, manager, user_id, data.is_active)
    except (PermissionError, LookupError, ValueError) as error:
        raise _convert_service_error(error) from error


@router.post(
    "/{user_id}/reset-password",
    response_model=UserCreatedResponse,
)
def reset_user_password_endpoint(
    user_id: UUID,
    db: Session = Depends(get_db),
    manager: User = Depends(require_permission("users.manage")),
):
    try:
        user, temporary_password = reset_user_password(db, manager, user_id)
    except (PermissionError, LookupError, ValueError) as error:
        raise _convert_service_error(error) from error
    return UserCreatedResponse(
        **UserResponse.model_validate(user).model_dump(),
        temporary_password=temporary_password,
    )
