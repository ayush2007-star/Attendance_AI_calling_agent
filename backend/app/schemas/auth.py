from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class UserScopeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    scope_type: str
    scope_value: str


class AuthenticatedUserResponse(BaseModel):
    id: UUID
    username: str
    email: str
    full_name: str
    role: str
    must_change_password: bool
    permissions: list[str] = Field(default_factory=list)
    scopes: list[UserScopeResponse] = Field(default_factory=list)


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(min_length=6, max_length=128)
