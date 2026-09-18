from datetime import date
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class AbsenceCreate(BaseModel):
    student_id: UUID
    attendance_record_id: UUID
    absence_date: date
    status: str = "PENDING"
    eligible_for_call: bool = True


class AbsenceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    student_id: UUID
    attendance_record_id: UUID
    absence_date: date
    status: str
    eligible_for_call: bool