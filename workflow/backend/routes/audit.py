"""Audit log query endpoints."""
from fastapi import APIRouter, Depends, Query
from typing import Optional, List

from models import AuditLog
from db import audit_logs
from routes.auth import require_audit_reader

router = APIRouter()


@router.get("/", response_model=List[AuditLog])
def list_audit_logs(
    user_id: Optional[str] = Query(None),
    action: Optional[str] = Query(None),
    resource_type: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=500),
    actor=Depends(require_audit_reader),
):
    logs = list(reversed(audit_logs))   # newest first
    if user_id:
        logs = [l for l in logs if l.user_id == user_id]
    if action:
        logs = [l for l in logs if l.action == action]
    if resource_type:
        logs = [l for l in logs if l.resource_type == resource_type]
    if search:
        s = search.lower()
        logs = [l for l in logs if s in l.resource_name.lower() or s in l.user_name.lower() or s in l.user_email.lower()]

    total = len(logs)
    start = (page - 1) * limit
    return logs[start: start + limit]


@router.get("/summary")
def audit_summary(actor=Depends(require_audit_reader)):
    from collections import Counter
    action_counts = Counter(l.action for l in audit_logs)
    resource_counts = Counter(l.resource_type for l in audit_logs)
    return {
        "total": len(audit_logs),
        "by_action": dict(action_counts.most_common(10)),
        "by_resource": dict(resource_counts.most_common(10)),
    }
