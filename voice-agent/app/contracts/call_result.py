from datetime import datetime
from pydantic import BaseModel


class CallResult(BaseModel):
    call_status: str
    transcript: str
    response_category: str | None = None
    followup_required: bool = False
    callback_at: datetime | None = None
    reason: str | None = None