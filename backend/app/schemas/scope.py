from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ScopeCreate(BaseModel):
    scope_type: Literal["department"] = "department"
    scope_value: str = Field(min_length=2, max_length=150)


class ScopeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    scope_type: str
    scope_value: str
