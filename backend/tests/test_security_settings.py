import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_production_settings_accept_https_origins_and_strong_secret() -> None:
    settings = Settings(
        _env_file=None,
        environment="production",
        database_url="postgresql+psycopg://user:password@localhost/database",
        jwt_secret_key="a" * 48,
        cors_allowed_origins="https://attendance.example.edu",
    )

    assert settings.cors_origins == ["https://attendance.example.edu"]


@pytest.mark.parametrize(
    ("secret", "origins"),
    [
        ("replace-this-secret", "https://attendance.example.edu"),
        ("a" * 48, "*"),
        ("a" * 48, "http://attendance.example.edu"),
    ],
)
def test_production_settings_reject_weak_secret_or_origins(
    secret: str,
    origins: str,
) -> None:
    with pytest.raises(ValidationError):
        Settings(
            _env_file=None,
            environment="production",
            database_url="postgresql+psycopg://user:password@localhost/database",
            jwt_secret_key=secret,
            cors_allowed_origins=origins,
        )


def test_production_settings_reject_demo_data_seeding() -> None:
    with pytest.raises(ValidationError):
        Settings(
            _env_file=None,
            environment="production",
            database_url="postgresql://localhost/database",
            jwt_secret_key="a" * 48,
            cors_allowed_origins="https://attendance.example.edu",
            auto_seed_demo_data=True,
        )
