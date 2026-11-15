from datetime import date
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class CallContext(BaseModel):
    model_config = ConfigDict(extra="ignore")

    campaign_target_id: UUID
    student_id: UUID
    student_name: str = Field(min_length=1, max_length=120)
    parent_name: str = Field(min_length=1, max_length=120)
    phone_number: str
    attendance_date: date
    preferred_language: str = "hi-IN"
    attendance_percentage: float = Field(default=0.0, ge=0.0, le=100.0)
    threshold: float = Field(default=75.0, ge=0.0, le=100.0)
    student_code: str = Field(default="")

    @field_validator("phone_number")
    @classmethod
    def phone_must_be_e164(cls, value: str) -> str:
        if not value.startswith("+") or not value[1:].isdigit():
            raise ValueError("phone_number must be an E.164 number, e.g. +919876543210")
        if not 8 <= len(value[1:]) <= 15:
            raise ValueError("phone_number must contain 8 to 15 digits")
        return value

    @field_validator("student_name", "parent_name")
    @classmethod
    def name_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("name must not be blank")
        return value.strip()


class StartCallRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    context: CallContext
    parent_contact_authorized: bool


class StartCallResponse(BaseModel):
    session_id: UUID
    provider_call_id: str
    status: str


class GuardianCheck(BaseModel):
    guardian_confirmed: bool


class StructuredAnalysis(BaseModel):
    response_category: Literal[
        "WILL_ATTEND",
        "MEDICAL_REASON",
        "LEAVE_RELATED",
        "CALLBACK_REQUESTED",
        "WILL_NOT_ATTEND",
        "WRONG_NUMBER",
        "DISPUTED",
        "OTHER",
    ] = "OTHER"
    reason_summary: str = ""
    followup_required: bool = False
    callback_at: str | None = None
    parent_sentiment: Literal[
        "cooperative", "neutral", "upset", "busy", "unreachable"
    ] = "neutral"
