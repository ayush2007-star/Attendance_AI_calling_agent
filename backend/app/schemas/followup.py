from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class FollowupCreate(BaseModel):
    student_id: UUID
    reason: str = Field(min_length=1, max_length=500)
    scheduled_for: datetime
    timezone_name: str = "UTC"
    conversation_id: UUID | None = None
    campaign_id: UUID | None = None
    campaign_target_id: UUID | None = None
    parent_id: UUID | None = None
    assigned_to: UUID | None = None
    priority: str = "MEDIUM"
    category: str = "OTHER"


class FollowupResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    student_id: UUID
    conversation_id: UUID | None
    campaign_id: UUID | None
    campaign_target_id: UUID | None
    parent_id: UUID | None
    reason: str
    priority: str
    status: str
    due_at: datetime | None
    scheduled_for: datetime | None
    timezone_name: str
    retry_count: int
    completed_at: datetime | None
