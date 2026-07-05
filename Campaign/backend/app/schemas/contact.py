"""Contact, custom field, and consent schemas."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, EmailStr, Field

from app.models.enums import Channel, ConsentStatus
from app.schemas.common import ORMModel


class ConsentOut(ORMModel):
    id: int
    channel: str
    status: str
    source: str | None = None
    updated_at: datetime


class ContactBase(BaseModel):
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=50)
    device_token: str | None = Field(default=None, max_length=512)
    first_name: str | None = Field(default=None, max_length=120)
    last_name: str | None = Field(default=None, max_length=120)
    country: str | None = Field(default=None, max_length=2)
    timezone: str | None = "UTC"
    tags: list[str] = Field(default_factory=list)
    attributes: dict[str, Any] = Field(default_factory=dict)


class ContactCreate(ContactBase):
    pass


class ContactUpdate(BaseModel):
    email: EmailStr | None = None
    phone: str | None = None
    device_token: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    country: str | None = None
    timezone: str | None = None
    tags: list[str] | None = None
    attributes: dict[str, Any] | None = None
    is_active: bool | None = None


class ContactOut(ORMModel):
    id: int
    email: str | None = None
    phone: str | None = None
    device_token: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    country: str | None = None
    timezone: str | None = None
    tags: list[str] = []
    attributes: dict[str, Any] = {}
    is_active: bool
    consents: list[ConsentOut] = []
    created_at: datetime


class BulkImportResult(BaseModel):
    received: int
    created: int
    updated: int
    skipped: int
    errors: list[str] = []


class CustomFieldCreate(BaseModel):
    key: str = Field(pattern=r"^[a-z][a-z0-9_]*$", max_length=100)
    label: str = Field(max_length=255)
    field_type: str = Field(default="string", pattern=r"^(string|number|bool|date)$")


class CustomFieldOut(ORMModel):
    id: int
    key: str
    label: str
    field_type: str


class ConsentUpdate(BaseModel):
    channel: Channel
    status: ConsentStatus
    source: str | None = None
    reason: str | None = None
