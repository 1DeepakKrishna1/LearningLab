"""User & auth domain models."""
from __future__ import annotations

from pydantic import BaseModel, Field

from .common import iso, new_id
from .enums import Role


class User(BaseModel):
    """A platform user (persisted in users.json). `password_hash` never leaves the backend."""

    id: str = Field(default_factory=new_id)
    email: str
    name: str = ""
    password_hash: str = ""
    role: Role = Role.VIEWER
    active: bool = True
    created_at: str = Field(default_factory=iso)


class UserPublic(BaseModel):
    """User projection safe to return over the API."""

    id: str
    email: str
    name: str
    role: Role
    active: bool

    @classmethod
    def of(cls, user: User) -> "UserPublic":
        return cls(id=user.id, email=user.email, name=user.name,
                   role=user.role, active=user.active)


class UserCreate(BaseModel):
    email: str
    name: str = ""
    password: str
    role: Role = Role.VIEWER


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserPublic
