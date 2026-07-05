"""Audit log domain model."""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from .common import iso, new_id
from .enums import AuditActor


class AuditEntry(BaseModel):
    """An immutable audit record (persisted in audit_logs.json)."""

    id: str = Field(default_factory=new_id)
    timestamp: str = Field(default_factory=iso)
    actor: AuditActor = AuditActor.SYSTEM
    actor_id: str | None = None
    workflow: str | None = None
    execution_id: str | None = None
    agent: str | None = None
    action: str = ""
    result: str = "success"          # success | error | info
    detail: dict[str, Any] = Field(default_factory=dict)
