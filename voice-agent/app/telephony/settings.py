from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


VOICE_AGENT_ROOT = Path(__file__).resolve().parents[2]


class TelephonySettings(BaseSettings):
    backend_base_url: str = "http://127.0.0.1:8000"
    real_calls_enabled: bool = False
    external_ai_processing_approved: bool = False

    public_base_url: str = ""
    call_api_key: str = ""
    database_url: str = ""

    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    twilio_from_number: str = ""

    deepgram_api_key: str = ""
    deepgram_model: str = "nova-3"
    deepgram_language: str = "multi"

    groq_api_key: str = ""
    groq_base_url: str = "https://api.groq.com/openai/v1"
    groq_model: str = "openai/gpt-oss-20b"
    groq_temperature: float = 0.2
    groq_max_tokens: int = 512

    cartesia_api_key: str = ""
    cartesia_model: str = "sonic-3.6"
    cartesia_voice_id: str = ""
    cartesia_version: str = "2026-08-14"

    tts_provider: str = "auto"
    edge_voice_hi: str = "hi-IN-MadhurNeural"
    edge_voice_en: str = "en-IN-NeerjaNeural"
    edge_voice_rate: str = "+25%"
    edge_voice_pitch: str = "+0Hz"

    assistant_gender: str = "male"
    voice_persona: str = "rural_warm"
    school_name: str = "BBS College of Engineering and Technology"
    max_call_seconds: int = Field(default=180, gt=0, le=600)
    max_conversation_turns: int = Field(default=6, gt=1, le=20)

    model_config = SettingsConfigDict(
        env_file=VOICE_AGENT_ROOT / ".env",
        env_file_encoding="utf-8",
        env_ignore_empty=True,
        extra="ignore",
    )


@lru_cache
def get_settings() -> TelephonySettings:
    return TelephonySettings()
