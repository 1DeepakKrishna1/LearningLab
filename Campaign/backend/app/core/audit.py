"""Audit logging helper."""
from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.models import AuditLog, User


def record_audit(
    db: Session,
    *,
    action: str,
    user: User | None = None,
    entity_type: str | None = None,
    entity_id: str | int | None = None,
    detail: dict[str, Any] | None = None,
    ip_address: str | None = None,
    commit: bool = True,
) -> AuditLog:
    """Persist an audit-log entry. Safe to call within request handlers."""
    entry = AuditLog(
        user_id=user.id if user else None,
        user_email=user.email if user else None,
        action=action,
        entity_type=entity_type,
        entity_id=str(entity_id) if entity_id is not None else None,
        detail=detail,
        ip_address=ip_address,
    )
    db.add(entry)
    if commit:
        db.commit()
    return entry
