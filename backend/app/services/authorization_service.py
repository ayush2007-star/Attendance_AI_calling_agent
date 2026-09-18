from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.authorization import Scope, user_scopes
from app.models.user import User


def resolve_scope_for_user(
    db: Session,
    user: User,
    requested_scope_id: UUID | None = None,
) -> UUID:
    if requested_scope_id is not None:
        scope_exists = db.execute(
            select(Scope.id).where(Scope.id == requested_scope_id)
        ).scalar_one_or_none()

        if scope_exists is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Scope not found",
            )

        if user.role != "SUPER_ADMIN":
            permitted_scope = db.execute(
                select(user_scopes.c.scope_id).where(
                    user_scopes.c.user_id == user.id,
                    user_scopes.c.scope_id == requested_scope_id,
                )
            ).scalar_one_or_none()

            if permitted_scope is None:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You do not have access to this scope",
                )

        return requested_scope_id

    default_scope = db.execute(
        select(user_scopes.c.scope_id)
        .where(user_scopes.c.user_id == user.id)
        .order_by(user_scopes.c.scope_id)
    ).scalar_one_or_none()

    if default_scope is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No scope is assigned to this user",
        )

    return default_scope
