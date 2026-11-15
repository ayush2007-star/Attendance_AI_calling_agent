from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ParentCreate(BaseModel):
    name: str
    primary_phone: str
    alternate_phone: str | None = None
    preferred_language: str = "hi-IN"
    is_active: bool = True
    call_consent: bool = False
    call_opt_out: bool = False


class ParentUpdate(BaseModel):
    name: str | None = None
    primary_phone: str | None = None
    alternate_phone: str | None = None
    preferred_language: str | None = None
    is_active: bool | None = None
    call_consent: bool | None = None
    call_opt_out: bool | None = None


class ParentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    primary_phone: str
    alternate_phone: str | None
    preferred_language: str
    is_active: bool
    call_consent: bool = False
    call_opt_out: bool = False
