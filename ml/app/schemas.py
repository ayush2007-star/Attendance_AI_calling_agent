from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class RepeatCallRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    student_id: UUID | str
    attendance_percentage: float = Field(ge=0.0, le=100.0)
    attendance_threshold: float = Field(default=75.0, ge=0.0, le=100.0)
    previous_call_count: int = Field(default=0, ge=0)
    previous_unanswered_count: int = Field(default=0, ge=0)
    days_since_last_call: int = Field(default=0, ge=0)
    last_response_category: str | None = None
    consecutive_absent_days: int = Field(default=0, ge=0)


class RepeatCallResponse(BaseModel):
    model_version: str
    repeat_call_score: float = Field(ge=0.0, le=1.0)
    recommended_priority: Literal["HIGH", "MEDIUM", "LOW"]
    recommended_followup: bool
    risk_factors: list[str] = Field(default_factory=list)


class OptimalTimingRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    student_id: UUID | str
    parent_relation: str = "GUARDIAN"
    preferred_language: str = "hi-IN"
    previous_unanswered_count: int = Field(default=0, ge=0)
    previous_successful_hour: int | None = Field(default=None, ge=0, le=23)
    is_rural: bool = True


class OptimalTimingResponse(BaseModel):
    model_version: str
    best_time_window: str
    best_day_of_week: str
    expected_answer_probability: float = Field(ge=0.0, le=1.0)
    reasoning: str


class DropoutRiskRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    student_id: UUID | str
    attendance_percentage: float = Field(ge=0.0, le=100.0)
    trend_slope: float = 0.0  # e.g. -2.5% per week
    approved_leave_count: int = Field(default=0, ge=0)
    unapproved_absent_count: int = Field(default=0, ge=0)
    semester: int = Field(default=1, ge=1, le=8)


class DropoutRiskResponse(BaseModel):
    model_version: str
    risk_level: Literal["CRITICAL", "HIGH_RISK", "MODERATE", "LOW_RISK"]
    dropout_probability: float = Field(ge=0.0, le=1.0)
    recommended_intervention: str
    key_indicators: list[str] = Field(default_factory=list)


class BatchRepeatCallRequest(BaseModel):
    items: list[RepeatCallRequest]


class BatchRepeatCallResponse(BaseModel):
    results: list[RepeatCallResponse]
