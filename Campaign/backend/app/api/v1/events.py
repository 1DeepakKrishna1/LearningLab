"""Event tracking ingestion: open pixel, click redirect, provider webhooks.

These endpoints are intentionally public (no JWT) because they are hit by
recipients' mail clients / browsers, or by external providers. They are
rate-limited globally and validate the delivery id.
"""
from __future__ import annotations

import base64
from datetime import datetime, timezone

from fastapi import APIRouter, Body, HTTPException, Query
from fastapi.responses import RedirectResponse, Response

from app.core.deps import DbSession
from app.models import Consent, Delivery, EventLog
from app.models.enums import Channel, ConsentStatus, EventType
from app.schemas.audit import EventIngest
from app.schemas.common import Message

router = APIRouter(prefix="/events", tags=["Event Tracking"])

# 1x1 transparent GIF.
_PIXEL = base64.b64decode(
    "R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7"
)


def _record(db, delivery: Delivery, event_type: str, metadata: dict | None = None) -> None:
    db.add(EventLog(
        delivery_id=delivery.id, campaign_id=delivery.campaign_id, contact_id=delivery.contact_id,
        channel=delivery.channel, event_type=event_type, event_metadata=metadata,
        occurred_at=datetime.now(timezone.utc),
    ))
    db.commit()


@router.get("/open/{delivery_id}.gif")
def track_open(db: DbSession, delivery_id: int):
    """Email open tracking pixel."""
    delivery = db.get(Delivery, delivery_id)
    if delivery:
        _record(db, delivery, EventType.OPENED.value)
    return Response(content=_PIXEL, media_type="image/gif")


@router.get("/click/{delivery_id}")
def track_click(db: DbSession, delivery_id: int, url: str = Query(...)):
    """Click tracking redirect."""
    delivery = db.get(Delivery, delivery_id)
    if delivery:
        _record(db, delivery, EventType.CLICKED.value, {"url": url})
    return RedirectResponse(url=url, status_code=302)


@router.post("/ingest", response_model=Message)
def ingest_event(db: DbSession, payload: EventIngest):
    """Generic event ingestion (e.g. provider webhook bridge)."""
    delivery = db.get(Delivery, payload.delivery_id)
    if not delivery:
        raise HTTPException(status_code=404, detail="Delivery not found")
    _record(db, delivery, payload.event_type, payload.event_metadata)
    return Message(message="recorded")


@router.post("/sms-keyword", response_model=Message)
def sms_keyword(
    db: DbSession,
    from_number: str = Body(..., embed=True),
    keyword: str = Body(..., embed=True),
):
    """Handle inbound SMS keywords: STOP / START / HELP (TCPA compliance)."""
    from sqlalchemy import select

    from app.models import Contact

    contact = db.scalar(select(Contact).where(Contact.phone == from_number))
    if not contact:
        raise HTTPException(status_code=404, detail="No contact for that number")

    keyword_up = keyword.strip().upper()
    consent = db.scalar(
        select(Consent).where(Consent.contact_id == contact.id, Consent.channel == Channel.SMS.value)
    )
    if not consent:
        consent = Consent(contact_id=contact.id, channel=Channel.SMS.value)
        db.add(consent)

    if keyword_up == "STOP":
        consent.status = ConsentStatus.UNSUBSCRIBED.value
        consent.source = "sms_stop"
        db.commit()
        return Message(message="You have been unsubscribed. Reply START to opt back in.")
    if keyword_up == "START":
        consent.status = ConsentStatus.SUBSCRIBED.value
        consent.source = "sms_start"
        db.commit()
        return Message(message="You have been re-subscribed.")
    if keyword_up == "HELP":
        return Message(message="Reply STOP to unsubscribe. Msg & data rates may apply.")
    return Message(message="Unknown keyword. Reply HELP for assistance.")
