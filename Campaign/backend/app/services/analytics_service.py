"""Analytics aggregation logic.

Computes per-campaign and overview metrics directly from ``event_logs`` and
``deliveries``. For large datasets these queries would be backed by the
``analytics_snapshots`` rollup table (see :func:`rebuild_snapshots`).
"""
from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Campaign, Contact, Delivery, EventLog
from app.models.enums import CampaignStatus, DeliveryStatus, EventType


def _safe_rate(numerator: int, denominator: int) -> float:
    return round(numerator / denominator, 4) if denominator else 0.0


def _event_counts(db: Session, campaign_id: int) -> dict[str, int]:
    rows = db.execute(
        select(EventLog.event_type, func.count())
        .where(EventLog.campaign_id == campaign_id)
        .group_by(EventLog.event_type)
    ).all()
    return {etype: cnt for etype, cnt in rows}


def campaign_metrics(db: Session, campaign: Campaign) -> dict:
    sent = db.scalar(
        select(func.count())
        .select_from(Delivery)
        .where(
            Delivery.campaign_id == campaign.id,
            Delivery.status.in_([DeliveryStatus.SENT.value, DeliveryStatus.DELIVERED.value]),
        )
    ) or 0
    counts = _event_counts(db, campaign.id)
    delivered = counts.get(EventType.DELIVERED.value, 0)
    opened = counts.get(EventType.OPENED.value, 0)
    clicked = counts.get(EventType.CLICKED.value, 0)
    bounced = counts.get(EventType.BOUNCED.value, 0)
    failed = counts.get(EventType.FAILED.value, 0)
    unsubscribed = counts.get(EventType.UNSUBSCRIBED.value, 0)
    converted = counts.get(EventType.CONVERTED.value, 0)
    replied = counts.get(EventType.REPLIED.value, 0)

    return {
        "campaign_id": campaign.id,
        "campaign_name": campaign.name,
        "channel": campaign.channel,
        "sent": sent,
        "delivered": delivered,
        "opened": opened,
        "clicked": clicked,
        "bounced": bounced,
        "failed": failed,
        "unsubscribed": unsubscribed,
        "converted": converted,
        "replied": replied,
        "delivery_rate": _safe_rate(delivered, sent),
        "open_rate": _safe_rate(opened, delivered or sent),
        "click_rate": _safe_rate(clicked, opened or delivered or sent),
        "bounce_rate": _safe_rate(bounced, sent),
        "failure_rate": _safe_rate(failed, sent),
        "reply_rate": _safe_rate(replied, sent),
        "conversion_rate": _safe_rate(converted, delivered or sent),
    }


def overview(db: Session) -> dict:
    total_campaigns = db.scalar(select(func.count()).select_from(Campaign)) or 0
    active = db.scalar(
        select(func.count())
        .select_from(Campaign)
        .where(
            Campaign.status.in_(
                [CampaignStatus.SCHEDULED.value, CampaignStatus.SENDING.value]
            )
        )
    ) or 0
    total_contacts = db.scalar(select(func.count()).select_from(Contact)) or 0

    def total_events(event_type: str) -> int:
        return db.scalar(
            select(func.count()).select_from(EventLog).where(EventLog.event_type == event_type)
        ) or 0

    sent = db.scalar(
        select(func.count())
        .select_from(Delivery)
        .where(Delivery.status.in_([DeliveryStatus.SENT.value, DeliveryStatus.DELIVERED.value]))
    ) or 0

    return {
        "total_campaigns": total_campaigns,
        "active_campaigns": active,
        "total_contacts": total_contacts,
        "sent": sent,
        "delivered": total_events(EventType.DELIVERED.value),
        "opened": total_events(EventType.OPENED.value),
        "clicked": total_events(EventType.CLICKED.value),
        "by_channel": {},
    }


def timeseries(db: Session, campaign_id: int | None = None, days: int = 30) -> list[dict]:
    """Daily event counts (sent/delivered/opened/clicked)."""
    date_expr = func.strftime("%Y-%m-%d", EventLog.occurred_at)
    stmt = select(date_expr.label("d"), EventLog.event_type, func.count())
    if campaign_id is not None:
        stmt = stmt.where(EventLog.campaign_id == campaign_id)
    stmt = stmt.group_by("d", EventLog.event_type).order_by("d")

    buckets: dict[str, dict] = {}
    for d, etype, cnt in db.execute(stmt).all():
        bucket = buckets.setdefault(d, {"date": d, "sent": 0, "delivered": 0, "opened": 0, "clicked": 0})
        if etype in bucket:
            bucket[etype] += cnt
    return list(buckets.values())[-days:]
