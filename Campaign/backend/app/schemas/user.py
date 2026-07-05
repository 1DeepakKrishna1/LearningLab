"""User and role schemas."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field

from app.schemas.common import ORMModel


class RoleOut(ORMModel):
    id: int
    name: str
    description: str = ""


class UserBase(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=1, max_length=255)


class UserCreate(UserBase):
    password: str = Field(min_length=8, max_length=128)
    roles: list[str] = Field(default_factory=lambda: ["viewer"])


class UserUpdate(BaseModel):
    full_name: str | None = Field(default=None, max_length=255)
    is_active: bool | None = None
    roles: list[str] | None = None


class UserProfileUpdate(BaseModel):
    full_name: str | None = Field(default=None, max_length=255)


class UserOut(ORMModel):
    id: int
    # str (not EmailStr) on output so loose/local addresses like ``admin@local`` serialize fine.
    email: str
    full_name: str
    is_active: bool
    roles: list[RoleOut] = []
    last_login_at: datetime | None = None
    created_at: datetime
