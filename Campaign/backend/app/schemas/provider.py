"""Provider configuration schemas."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.models.enums import Channel, ProviderType
from app.schemas.common import ORMModel


class ProviderConfigBase(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    channel: Channel
    provider_type: ProviderType
    config: dict[str, Any] = Field(default_factory=dict)
    mode: str = Field(default="console", pattern=r"^(console|live)$")
    is_default: bool = False
    is_active: bool = True


class ProviderConfigCreate(ProviderConfigBase):
    pass


class ProviderConfigUpdate(BaseModel):
    name: str | None = None
    config: dict[str, Any] | None = None
    mode: str | None = Field(default=None, pattern=r"^(console|live)$")
    is_default: bool | None = None
    is_active: bool | None = None


class ProviderConfigOut(ORMModel):
    id: int
    name: str
    channel: str
    provider_type: str
    config: dict[str, Any]
    mode: str
    is_default: bool
    is_active: bool
    last_health_status: str | None = None
    last_health_checked_at: datetime | None = None
    created_at: datetime


class HealthCheckResult(BaseModel):
    healthy: bool
    status: str
    detail: str | None = None
