from datetime import date
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class AttendanceImportCreate(BaseModel):
    file_name: str = Field(min_length=1, max_length=255)
    file_type: str = Field(min_length=1, max_length=20)
    attendance_date: date
    class_id: UUID | None = None


class AttendanceImportResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    file_name: str
    file_type: str
    attendance_date: date
    class_id: UUID | None
    total_rows: int
    valid_rows: int
    invalid_rows: int
    duplicate_rows: int
    status: str
    uploaded_by: UUID