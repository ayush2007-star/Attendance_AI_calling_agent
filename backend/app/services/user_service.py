import secrets
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.authorization import Role, Scope, user_scopes
from app.models.user import User
from app.schemas.user import UserCreate


ROLE_CREATION_POLICY = {
    "SUPER_ADMIN": {"ADMIN", "STAFF"},
    "ADMIN": {"STAFF"},
}


def _managed_scope_ids(db: Session, manager: User) -> set[UUID]:
    return set(
        db.scalars(
            select(user_scopes.c.scope_id).where(
                user_scopes.c.user_id == manager.id
            )
        ).all()
    )


def _check_manager_scope(
    db: Session,
    manager: User,
    requested_scope_ids: set[UUID],
) -> list[Scope]:
    if not requested_scope_ids:
        raise ValueError("Assign at least one department scope")

    if manager.role != "SUPER_ADMIN":
        permitted_scope_ids = _managed_scope_ids(db, manager)
        if not requested_scope_ids.issubset(permitted_scope_ids):
            raise PermissionError("You cannot assign a user outside your department")

    scopes = list(
        db.scalars(
            select(Scope).where(Scope.id.in_(requested_scope_ids))
        ).all()
    )
    if len(scopes) != len(requested_scope_ids):
        raise ValueError("One or more selected departments do not exist")
    return scopes


def _get_managed_user(db: Session, manager: User, target_id: UUID) -> User:
    target = db.get(User, target_id)
    if target is None:
        raise LookupError("User not found")
    if target.id == manager.id:
        raise PermissionError("You cannot manage your own account here")
    if manager.role == "SUPER_ADMIN":
        return target
    if manager.role != "ADMIN" or target.role != "STAFF":
        raise PermissionError("HODs can manage teachers in their own department only")

    manager_scopes = _managed_scope_ids(db, manager)
    target_scopes = {
        scope_id
        for (scope_id,) in db.execute(
            select(user_scopes.c.scope_id).where(
                user_scopes.c.user_id == target.id
            )
        ).all()
    }
    if not manager_scopes.intersection(target_scopes):
        raise PermissionError("This teacher is outside your department")
    return target


def get_users(db: Session, manager: User) -> list[User]:
    query = select(User).order_by(User.full_name, User.username)
    if manager.role != "SUPER_ADMIN":
        if manager.role != "ADMIN":
            raise PermissionError("Only directors and HODs can view user accounts")
        managed_ids = select(user_scopes.c.user_id).where(
            user_scopes.c.scope_id.in_(_managed_scope_ids(db, manager))
        )
        query = query.where(User.role == "STAFF", User.id.in_(managed_ids))
    return list(db.scalars(query).unique().all())


def create_user(
    db: Session,
    data: UserCreate,
    manager: User,
) -> tuple[User, str]:
    allowed_roles = ROLE_CREATION_POLICY.get(manager.role, set())
    if data.role not in allowed_roles:
        raise PermissionError(
            "Directors can add HODs or teachers; HODs can add teachers only"
        )

    normalized_email = str(data.email).strip().lower()
    normalized_username = data.username.strip()
    duplicate = db.execute(
        select(User.id).where(
            or_(
                func.lower(User.username) == normalized_username.lower(),
                func.lower(User.email) == normalized_email,
            )
        )
    ).scalar_one_or_none()
    if duplicate is not None:
        raise ValueError("That username or email is already in use")

    if len(set(data.scope_ids)) != len(data.scope_ids):
        raise ValueError("A department can be selected only once")
    scopes = _check_manager_scope(db, manager, set(data.scope_ids))

    role = db.execute(
        select(Role).where(Role.name == data.role)
    ).scalar_one_or_none()
    if role is None:
        raise RuntimeError("The user-role migration has not been applied")

    custom_password = data.password.strip() if (data.password and data.password.strip()) else None
    assigned_password = custom_password or secrets.token_urlsafe(16)
    user = User(
        username=normalized_username,
        email=normalized_email,
        password_hash=hash_password(assigned_password),
        full_name=data.full_name.strip(),
        role=data.role,
        is_active=True,
        must_change_password=False if custom_password else True,
        roles=[role],
        scopes=scopes,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user, assigned_password


def set_user_active(
    db: Session,
    manager: User,
    target_id: UUID,
    is_active: bool,
) -> User:
    target = _get_managed_user(db, manager, target_id)
    target.is_active = is_active
    db.commit()
    db.refresh(target)
    return target


def reset_user_password(
    db: Session,
    manager: User,
    target_id: UUID,
    new_password: str | None = None,
) -> tuple[User, str]:
    target = _get_managed_user(db, manager, target_id)
    assigned_password = new_password.strip() if (new_password and new_password.strip()) else secrets.token_urlsafe(16)
    target.password_hash = hash_password(assigned_password)
    target.must_change_password = False if new_password else True
    db.commit()
    db.refresh(target)
    return target, assigned_password
