from datetime import datetime
from uuid import UUID

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
