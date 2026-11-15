from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.jwt import create_access_token
from app.core.security import verify_password
from app.models.user import User
from app.schemas.auth import LoginRequest, TokenResponse


def authenticate_user(
    db: Session,
    data: LoginRequest,
) -> TokenResponse | None:
    search_term = data.username.strip()
    result = db.execute(
        select(User).where(
            or_(
                func.lower(User.username) == search_term.lower(),
                func.lower(User.email) == search_term.lower(),
            )
        )
    )

    user = result.scalar_one_or_none()

    if user is None:
        return None

    if not user.is_active:
        return None

    if not verify_password(data.password, user.password_hash):
        return None

    access_token = create_access_token(
        user_id=str(user.id),
        role=user.role,
    )

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=settings.access_token_expire_minutes * 60,
    )
