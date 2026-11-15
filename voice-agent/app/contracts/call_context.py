from datetime import date
from uuid import UUID

from pydantic import BaseModel, ConfigDict, PrivateAttr


class CallContext(BaseModel):
    model_config = ConfigDict(extra="forbid")

    _is_synthetic: bool = PrivateAttr(default=False)

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

    @property
    def is_synthetic(self) -> bool:
        return self._is_synthetic

    @classmethod
    def from_synthetic_data(cls, data: dict[str, object]) -> "CallContext":
        context = cls.model_validate(data)
        context._is_synthetic = True
        return context
