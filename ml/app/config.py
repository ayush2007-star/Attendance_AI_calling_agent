from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


ML_ROOT = Path(__file__).resolve().parents[1]


class MLSettings(BaseSettings):
    ml_env: str = "development"
    ml_port: int = 8002
    ml_host: str = "0.0.0.0"
    model_version: str = "v1"
    models_dir: str = "models/v1"

    # Repeat call probability thresholds
    repeat_call_high_threshold: float = 0.70
    repeat_call_med_threshold: float = 0.40

    # Dropout risk thresholds
    dropout_critical_threshold: float = 0.75
    dropout_high_threshold: float = 0.50
    dropout_moderate_threshold: float = 0.25

    model_config = SettingsConfigDict(
        env_file=ML_ROOT / ".env",
        env_file_encoding="utf-8",
        env_ignore_empty=True,
        extra="ignore",
    )

    @property
    def full_models_path(self) -> Path:
        base = Path(self.models_dir)
        if not base.is_absolute():
            return ML_ROOT / base
        return base


@lru_cache
def get_ml_settings() -> MLSettings:
    return MLSettings()
