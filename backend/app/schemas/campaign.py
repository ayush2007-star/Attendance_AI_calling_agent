from datetime import date, datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field


class CampaignCreate(BaseModel):
    name: str = Field(
        min_length=1,
        max_length=200,
    )

    attendance_date: date

    class_id: UUID | None = None
    threshold: float | None = Field(default=None, ge=0, le=100)


class CampaignResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    attendance_date: date
    attendance_period_start: date
    attendance_period_end: date
    threshold_used: float
    class_id: UUID | None
    status: str
    total_targets: int
    completed_calls: int
    failed_calls: int
    created_by: UUID
    started_at: datetime | None
    completed_at: datetime | None


class CampaignTargetResponse(BaseModel):
    id: UUID
    student_id: UUID
    student_code: str
    roll_number: str
    student_name: str
    parent_name: str | None
    phone_number: str | None
    attendance_percentage: float
    threshold: float
    eligibility_reason: str
    status: str