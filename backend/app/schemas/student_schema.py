from uuid import UUID

from pydantic import BaseModel, ConfigDict


class StudentCreate(BaseModel):
    student_code: str
    roll_number: str
    first_name: str
    last_name: str | None = None
    class_id: UUID
    email: str | None = None
    is_active: bool = True


class StudentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    student_code: str
    roll_number: str
    first_name: str
    last_name: str | None
    class_id: UUID
    email: str | None
    is_active: bool