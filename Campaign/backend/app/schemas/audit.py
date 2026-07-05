"""Audit log and delivery/event schemas."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from app.schemas.common import ORMModel


class AuditLogOut(ORMModel):
    id: int
    user_id: int | None = None
    user_email: str | None = None
    action: str
    entity_type: str | None = None
    entity_id: str | None = None
    detail: dict[str, Any] | None = None
    ip_address: str | None = None
    created_at: datetime


class DeliveryOut(ORMModel):
    id: int
    campaign_id: int
    contact_id: int
    channel: str
    status: str
    provider: str | None = None
    provider_message_id: str | None = None
    error: str | None = None
    attempts: int
    sent_at: datetime | None = None
    created_at: datetime


class EventLogOut(ORMModel):
    id: int
    delivery_id: int | None = None
    campaign_id: int
    contact_id: int | None = None
    channel: str
    event_type: str
    occurred_at: datetime


class EventIngest(ORMModel):
    delivery_id: int
    event_type: str
    event_metadata: dict[str, Any] | None = None
