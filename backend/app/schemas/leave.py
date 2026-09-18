from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class LeaveCreate(BaseModel):
    student_id: UUID
    start_date: date
    end_date: date
    reason: str = Field(min_length=1)
    source: str = "MANUAL"
    notes: str | None = None

    @model_validator(mode="after")
    def validate_date_range(self) -> "LeaveCreate":
        if self.end_date < self.start_date:
            raise ValueError("end_date cannot be before start_date")
        return self


class LeaveResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    student_id: UUID
    start_date: date
    end_date: date
    reason: str
    status: str
    approved_by: UUID | None
    approved_at: datetime | None
    source: str
    notes: str | None
