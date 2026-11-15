from getpass import getpass
import re

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.authorization import Role, Scope
from app.models.user import User


def create_first_admin(
    db: Session,
    *,
    username: str,
    email: str,
    full_name: str,
    password: str,
) -> User:
    if not re.fullmatch(r"[A-Za-z0-9._-]{3,100}", username.strip()):
        raise ValueError(
            "Username must be 3-100 characters using letters, numbers, '.', '_' or '-'"
        )
    if not email.strip() or len(email.strip()) > 255 or "@" not in email:
        raise ValueError("Enter a valid email address")
    if not full_name.strip() or len(full_name.strip()) > 200:
        raise ValueError("Full name must be between 1 and 200 characters")
    user_count = db.scalar(select(func.count(User.id))) or 0
    if user_count:
        raise ValueError(
            "Admin bootstrap is available only before the first user is created"
        )
    if len(password) < 14:
        raise ValueError("Use a password with at least 14 characters")

    role = db.execute(
        select(Role).where(Role.name == "SUPER_ADMIN")
    ).scalar_one_or_none()
    scope = db.execute(
        select(Scope).where(
            Scope.scope_type == "college",
            Scope.scope_value == "default",
        )
    ).scalar_one_or_none()
    if role is None:
        raise RuntimeError(
            "Authorization migrations are missing; run alembic upgrade head first"
        )
    if scope is None:
        scope = Scope(
            scope_type="college",
            scope_value="default",
        )
        db.add(scope)
        db.flush()

    user = User(
        username=username.strip(),
        email=email.strip().lower(),
        full_name=full_name.strip(),
        password_hash=hash_password(password),
        role="SUPER_ADMIN",
        is_active=True,
        roles=[role],
        scopes=[scope],
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def main() -> None:
    print("Create the initial institution administrator.")
    print("This command works only when the database has no users.")
    username = input("Username: ").strip()
    email = input("Email: ").strip()
    full_name = input("Full name: ").strip()
    password = getpass("Password (14+ characters): ")
    confirmation = getpass("Confirm password: ")
    if password != confirmation:
        raise SystemExit("Passwords do not match.")

    with SessionLocal() as db:
        try:
            user = create_first_admin(
                db,
                username=username,
                email=email,
                full_name=full_name,
                password=password,
            )
        except ValueError as error:
            raise SystemExit(str(error)) from error
    print(f"Administrator {user.username!r} created successfully.")


if __name__ == "__main__":
    main()
