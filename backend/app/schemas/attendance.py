from datetime import date
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class AttendanceCreate(BaseModel):
    student_id: UUID
    attendance_date: date
    status: str
    source_type: str
    source_reference: str | None = None
    import_batch_id: UUID | None = None


class AttendanceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    student_id: UUID
    attendance_date: date
    status: str
    source_type: str
    source_reference: str | None
    import_batch_id: UUID | None