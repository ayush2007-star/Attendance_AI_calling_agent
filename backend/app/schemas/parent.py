from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ParentCreate(BaseModel):
    name: str
    primary_phone: str
    alternate_phone: str | None = None
    preferred_language: str = "en"
    is_active: bool = True


class ParentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    primary_phone: str
    alternate_phone: str | None
    preferred_language: str
    is_active: bool