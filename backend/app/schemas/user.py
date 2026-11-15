from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.schemas.auth import UserScopeResponse


class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=100, pattern=r"^[A-Za-z0-9._-]+$")
    email: EmailStr
    full_name: str = Field(min_length=1, max_length=200)
    role: Literal["ADMIN", "STAFF"]
    scope_ids: list[UUID] = Field(min_length=1, max_length=20)
    password: str | None = Field(default=None, min_length=6, max_length=128)


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    username: str
    email: str
    full_name: str
    role: str
    is_active: bool
    must_change_password: bool
    scopes: list[UserScopeResponse]


class UserCreatedResponse(UserResponse):
    temporary_password: str


class UserStatusUpdate(BaseModel):
    is_active: bool
