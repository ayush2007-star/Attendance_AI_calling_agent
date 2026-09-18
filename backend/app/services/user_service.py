from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.authorization import Role
from app.models.user import User
from app.schemas.user import UserCreate


def create_user(
    db: Session,
    data: UserCreate,
) -> User:
    role_name = data.role.upper()
    role = db.execute(
        select(Role).where(Role.name == role_name)
    ).scalar_one_or_none()

    if role is None:
        raise ValueError(f"Unknown role: {data.role}")

    user = User(
        username=data.username,
        email=data.email,
        password_hash=hash_password(data.password),
        full_name=data.full_name,
        role=role_name,
        is_active=data.is_active,
    )
    user.roles.append(role)

    db.add(user)
    db.commit()
    db.refresh(user)

    return user