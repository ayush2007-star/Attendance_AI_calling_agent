from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ClassCreate(BaseModel):
    course_name: str
    year: int
    semester: int
    section: str
    academic_year: str
    class_teacher_id: UUID | None = None
    scope_id: UUID | None = None
    is_active: bool = True


class ClassResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    course_name: str
    year: int
    semester: int
    section: str
    academic_year: str
    class_teacher_id: UUID | None
    scope_id: UUID
    is_active: bool