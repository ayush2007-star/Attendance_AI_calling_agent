from uuid import UUID

from pydantic import BaseModel, ConfigDict


class StudentParentCreate(BaseModel):
    student_id: UUID
    parent_id: UUID
    relationship_type: str
    is_primary: bool = False


class StudentParentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    student_id: UUID
    parent_id: UUID
    relationship_type: str
    is_primary: bool