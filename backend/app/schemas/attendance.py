from datetime import date
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class AttendanceCreate(BaseModel):
    student_id: UUID
    attendance_date: date
    status: str
    source_type: str = "MANUAL"
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


class AttendanceStudentItem(BaseModel):
    student_id: UUID
    status: Literal["PRESENT", "ABSENT", "LATE", "EXCUSED"]


class BulkAttendanceCreate(BaseModel):
    class_id: UUID
    attendance_date: date
    source_reference: str | None = "Roll Call Terminal"
    records: list[AttendanceStudentItem]


class QuickToggleRequest(BaseModel):
    student_id: UUID
    attendance_date: date
    new_status: Literal["PRESENT", "ABSENT", "LATE", "EXCUSED"]
