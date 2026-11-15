from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.db.dependencies import get_db
from app.core.security import hash_password, verify_password
from app.models.authorization import (
    Permission,
    Scope,
    role_permissions,
    user_roles,
    user_scopes,
)
from app.models.user import User
from app.schemas.auth import (
    AuthenticatedUserResponse,
    ChangePasswordRequest,
    LoginRequest,
    TokenResponse,
)
from app.services.auth_service import authenticate_user


router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
)


@router.post(
    "/login",
    response_model=TokenResponse,
)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    data = LoginRequest(
        username=form_data.username,
        password=form_data.password,
    )

    token = authenticate_user(db, data)

    if token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )

    return token


@router.get(
    "/me",
    response_model=AuthenticatedUserResponse,
)
def current_user(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AuthenticatedUserResponse:
    permissions = db.scalars(
        select(Permission.name)
        .join(role_permissions, role_permissions.c.permission_id == Permission.id)
        .join(user_roles, user_roles.c.role_id == role_permissions.c.role_id)
        .where(user_roles.c.user_id == user.id)
        .order_by(Permission.name)
    ).all()

    scope_query = select(Scope).order_by(Scope.scope_type, Scope.scope_value)
    if user.role != "SUPER_ADMIN":
        scope_query = (
            scope_query.join(user_scopes, user_scopes.c.scope_id == Scope.id)
            .where(user_scopes.c.user_id == user.id)
        )
    scopes = db.scalars(scope_query).all()

    return AuthenticatedUserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        must_change_password=user.must_change_password,
        permissions=list(permissions),
        scopes=scopes,
    )


@router.post("/change-password", status_code=status.HTTP_204_NO_CONTENT)
def change_password(
    data: ChangePasswordRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    if not verify_password(data.current_password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )
    if data.current_password == data.new_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be different from the current password",
        )

    user.password_hash = hash_password(data.new_password)
    user.must_change_password = False
    db.commit()