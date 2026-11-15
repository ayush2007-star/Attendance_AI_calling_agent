from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class StudentParentCreate(BaseModel):
    student_id: UUID
    parent_id: UUID
    relationship_type: str = Field(min_length=1, max_length=50)
    is_primary: bool = False


class StudentParentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    student_id: UUID
    parent_id: UUID
    relationship_type: str
    is_primary: bool