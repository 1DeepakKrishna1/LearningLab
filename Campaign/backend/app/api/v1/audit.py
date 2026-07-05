"""Audit log and delivery query endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select

from app.core.deps import DbSession, require_admin, require_viewer
from app.models import AuditLog, Delivery, EventLog
from app.schemas.audit import AuditLogOut, DeliveryOut, EventLogOut
from app.schemas.common import Page

router = APIRouter(tags=["Audit & Activity"])


@router.get("/audit-logs", response_model=Page[AuditLogOut], dependencies=[Depends(require_admin)])
def list_audit_logs(
    db: DbSession,
    action: str | None = None,
    entity_type: str | None = None,
    user_id: int | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
):
    stmt = select(AuditLog)
    if action:
        stmt = stmt.where(AuditLog.action == action)
    if entity_type:
        stmt = stmt.where(AuditLog.entity_type == entity_type)
    if user_id:
        stmt = stmt.where(AuditLog.user_id == user_id)
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    items = list(db.scalars(stmt.order_by(AuditLog.created_at.desc())
                            .offset((page - 1) * page_size).limit(page_size)))
    return Page[AuditLogOut](items=items, total=total, page=page, page_size=page_size)


@router.get("/campaigns/{campaign_id}/deliveries", response_model=Page[DeliveryOut],
            dependencies=[Depends(require_viewer)])
def list_deliveries(
    db: DbSession,
    campaign_id: int,
    status_filter: str | None = Query(default=None, alias="status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
):
    stmt = select(Delivery).where(Delivery.campaign_id == campaign_id)
    if status_filter:
        stmt = stmt.where(Delivery.status == status_filter)
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    items = list(db.scalars(stmt.order_by(Delivery.id.desc())
                            .offset((page - 1) * page_size).limit(page_size)))
    return Page[DeliveryOut](items=items, total=total, page=page, page_size=page_size)


@router.get("/campaigns/{campaign_id}/events", response_model=list[EventLogOut],
            dependencies=[Depends(require_viewer)])
def list_events(db: DbSession, campaign_id: int, limit: int = Query(200, le=1000)):
    stmt = (select(EventLog).where(EventLog.campaign_id == campaign_id)
            .order_by(EventLog.occurred_at.desc()).limit(limit))
    return list(db.scalars(stmt))
