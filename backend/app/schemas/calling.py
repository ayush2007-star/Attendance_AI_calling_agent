from datetime import date, datetime
from typing import Any, Literal
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field


class CallAttemptResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    campaign_id: UUID
    campaign_target_id: UUID | None
    parent_id: UUID
    attempt_number: int
    phone_number: str
    status: str
    provider_call_id: str | None
    started_at: datetime | None
    ended_at: datetime | None
    duration_seconds: int | None
    failure_reason: str | None


class CallContextResponse(BaseModel):
    campaign_target_id: UUID
    campaign_id: UUID

    student_id: UUID
    student_name: str
    student_code: str

    parent_id: UUID
    parent_name: str
    phone_number: str
    preferred_language: str

    attendance_percentage: float
    threshold: float
    eligibility_reason: str

    attendance_date: date
    attendance_period_start: date
    attendance_period_end: date


class CallStatusUpdate(BaseModel):
    status: str


class TranscriptTurnPayload(BaseModel):
    speaker: str  # "AGENT" or "PARENT"
    text: str
    confidence: float | None = 0.95
    sequence_number: int | None = None


class CallAnalysisPayload(BaseModel):
    category: str = "OTHER"
    summary: str = ""
    followup_required: bool = False
    callback_at: datetime | None = None
    confidence: float | None = 0.92
    model_name: str = "openai/gpt-oss-20b (via Groq)"
    sentiment: str = "neutral"
    raw_dict: dict[str, Any] | None = None


class CallCompletionPayload(BaseModel):
    provider_call_id: str
    attempt_id: UUID | None = None
    status: str = "COMPLETED"  # COMPLETED, FAILED, NO_ANSWER, BUSY
    duration_seconds: int | None = None
    language: str = "hi-IN"
    failure_reason: str | None = None
    turns: list[TranscriptTurnPayload] = Field(default_factory=list)
    analysis: CallAnalysisPayload | None = None
    is_demo: bool = False


class TranscriptItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    speaker: str
    text: str
    sequence_number: int
    confidence: float | None


class AIAnalysisResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    category: str
    summary: str | None
    followup_required: bool
    confidence: float | None
    model_name: str
    model_version: str | None


class ConversationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    call_attempt_id: UUID
    started_at: datetime | None
    ended_at: datetime | None
    language: str
    status: str
    transcripts: list[TranscriptItemResponse] = Field(default_factory=list)
    analysis: AIAnalysisResponse | None = None


class CallAttemptDetailResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    campaign_id: UUID
    campaign_name: str | None = None
    campaign_target_id: UUID | None = None
    student_id: UUID | None = None
    student_name: str | None = None
    student_roll: str | None = None
    parent_id: UUID
    parent_name: str | None = None
    attempt_number: int
    phone_number: str
    status: str
    provider_call_id: str | None
    started_at: datetime | None
    ended_at: datetime | None
    duration_seconds: int | None
    failure_reason: str | None
    is_demo: bool = False
    conversation: ConversationResponse | None = None


class VoiceServiceStatusResponse(BaseModel):
    service_online: bool
    voice_agent_url: str
    real_calls_enabled: bool
    external_ai_approved: bool
    calling_provider: str
    configured_model: str
    tts_provider: str
    school_name: str
    twilio_configured: bool
    deepgram_configured: bool
    groq_configured: bool


class DemoCallSimulateRequest(BaseModel):
    campaign_target_id: UUID | None = None
    student_id: UUID | None = None
    reason_preset: Literal[
        "MEDICAL_REASON",
        "WILL_ATTEND",
        "CALLBACK_REQUESTED",
        "OUT_OF_STATION",
        "WRONG_NUMBER",
        "DISPUTED",
    ] = "MEDICAL_REASON"
    custom_parent_reply: str | None = None
