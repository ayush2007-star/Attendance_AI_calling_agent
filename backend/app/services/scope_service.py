from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.authorization import Scope, user_scopes
from app.models.user import User
from app.schemas.scope import ScopeCreate


def get_scopes(db: Session, current_user: User) -> list[Scope]:
    query = select(Scope).order_by(Scope.scope_type, Scope.scope_value)
    if current_user.role != "SUPER_ADMIN":
        query = query.join(
            user_scopes,
            user_scopes.c.scope_id == Scope.id,
        ).where(user_scopes.c.user_id == current_user.id)
    return list(db.scalars(query).all())


def create_scope(db: Session, data: ScopeCreate) -> Scope:
    scope_value = data.scope_value.strip()
    existing = db.execute(
        select(Scope.id).where(
            Scope.scope_type == data.scope_type,
            Scope.scope_value.ilike(scope_value),
        )
    ).scalar_one_or_none()
    if existing is not None:
        raise ValueError("A department with this name already exists")

    scope = Scope(scope_type=data.scope_type, scope_value=scope_value)
    db.add(scope)
    db.commit()
    db.refresh(scope)
    return scope
