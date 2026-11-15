from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Attendance AI Agent"
    app_version: str = "1.0.0"
    environment: str = "development"

    database_url: str

    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    cors_allowed_origins: str = ""
    auto_seed_demo_data: bool = False

    # Voice Agent & Calling Settings (Safe defaults)
    real_calls_enabled: bool = False
    external_ai_processing_approved: bool = False
    voice_agent_base_url: str = "http://127.0.0.1:8001"
    voice_agent_api_key: str = ""
    calling_provider: str = "mock"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def cors_origins(self) -> list[str]:
        return [
            origin.strip()
            for origin in self.cors_allowed_origins.split(",")
            if origin.strip()
        ]

    @model_validator(mode="after")
    def validate_production_settings(self):
        if self.access_token_expire_minutes < 1:
            raise ValueError("ACCESS_TOKEN_EXPIRE_MINUTES must be positive")

        if self.environment.lower() == "production":
            if self.auto_seed_demo_data:
                raise ValueError(
                    "AUTO_SEED_DEMO_DATA must be disabled in production"
                )
            if len(self.jwt_secret_key) < 32 or "replace" in self.jwt_secret_key.lower():
                raise ValueError(
                    "Production JWT_SECRET_KEY must be at least 32 characters "
                    "and must not be a placeholder"
                )
            if "*" in self.cors_origins:
                raise ValueError(
                    "Wildcard CORS origins are not allowed in production"
                )
            if any(not origin.startswith("https://") for origin in self.cors_origins):
                raise ValueError(
                    "Production CORS origins must use HTTPS"
                )
        return self


settings = Settings()