from datetime import datetime
from uuid import UUID
from datetime import date, datetime
from pydantic import BaseModel, ConfigDict


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