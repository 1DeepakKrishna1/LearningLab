"""Campaign execution engine.

Resolves a campaign's audience, renders per-contact content, enforces consent,
sends through the provider factory (with retry), and records deliveries +
events. Runs as an asyncio task; uses its own DB session so it is safe to launch
from FastAPI BackgroundTasks or the scheduler loop.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import SessionLocal
from app.execution import dlq
from app.models import Campaign, Consent, Contact, Delivery, EventLog, Segment, Template
from app.models.enums import (
    CampaignStatus,
    Channel,
    ConsentStatus,
    DeliveryStatus,
    EventType,
)
from app.providers import Message, get_provider_factory
from app.services import segment_engine, template_service

logger = logging.getLogger("app.execution.engine")


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _resolve_audience(db: Session, campaign: Campaign) -> list[Contact]:
    if campaign.segment_id:
        seg = db.get(Segment, campaign.segment_id)
        if seg and seg.definition:
            return segment_engine.evaluate(db, seg.definition)
    # No segment -> all active contacts (bounded by batch logic).
    return list(db.scalars(select(Contact).where(Contact.is_active.is_(True))))


def _has_consent(db: Session, contact_id: int, channel: str) -> bool:
    consent = db.scalar(
        select(Consent).where(Consent.contact_id == contact_id, Consent.channel == channel)
    )
    # Absence of a record defaults to subscribed (opt-out model); unsubscribed blocks.
    return consent is None or consent.status == ConsentStatus.SUBSCRIBED.value


def _recipient_address(contact: Contact, channel: str) -> str | None:
    if channel == Channel.EMAIL.value:
        return contact.email
    if channel == Channel.SMS.value:
        return contact.phone
    if channel == Channel.PUSH.value:
        return contact.device_token
    return None


async def _send_one(
    db: Session,
    factory,
    campaign: Campaign,
    contact: Contact,
    template: Template | None,
    channel: str,
    step_id: int | None = None,
) -> None:
    delivery = Delivery(
        campaign_id=campaign.id,
        step_id=step_id,
        contact_id=contact.id,
        channel=channel,
        status=DeliveryStatus.PENDING.value,
    )
    db.add(delivery)
    db.flush()  # obtain delivery.id

    address = _recipient_address(contact, channel)
    if not address:
        delivery.status = DeliveryStatus.SKIPPED.value
        delivery.error = "no destination address for channel"
        db.commit()
        return

    if not _has_consent(db, contact.id, channel):
        delivery.status = DeliveryStatus.SKIPPED.value
        delivery.error = "contact not subscribed"
        db.commit()
        return

    rendered = template_service.render_for_contact(template, contact) if template else {"subject": None, "body": ""}
    message = Message(
        to=address,
        subject=rendered.get("subject"),
        body=rendered.get("body", ""),
        html=rendered.get("body") if channel == Channel.EMAIL.value else None,
        title=rendered.get("subject"),
        image_url=rendered.get("image_url"),
        deep_link=rendered.get("deep_link"),
        buttons=rendered.get("buttons", []),
    )

    provider = factory.get_for_channel(channel)
    delivery.provider = provider.name
    delivery.rendered_subject = rendered.get("subject")
    delivery.rendered_body = rendered.get("body")
    delivery.attempts += 1

    result = await factory.send_with_retry(provider, message)

    if result.success:
        delivery.status = DeliveryStatus.SENT.value
        delivery.provider_message_id = result.message_id
        delivery.sent_at = _utcnow()
        db.add(EventLog(
            delivery_id=delivery.id, campaign_id=campaign.id, contact_id=contact.id,
            channel=channel, event_type=EventType.SENT.value, occurred_at=_utcnow(),
        ))
        # Synthetic downstream events (console/sandbox adapters) for demo analytics.
        for ev in result.synthetic_events:
            db.add(EventLog(
                delivery_id=delivery.id, campaign_id=campaign.id, contact_id=contact.id,
                channel=channel, event_type=ev, occurred_at=_utcnow(),
            ))
        if result.synthetic_events and EventType.DELIVERED.value in result.synthetic_events:
            delivery.status = DeliveryStatus.DELIVERED.value
    else:
        delivery.status = DeliveryStatus.FAILED.value
        delivery.error = result.error
        db.add(EventLog(
            delivery_id=delivery.id, campaign_id=campaign.id, contact_id=contact.id,
            channel=channel, event_type=EventType.FAILED.value, occurred_at=_utcnow(),
        ))
        dlq.dead_letter(delivery.id, campaign.id, contact.id, result.error or "unknown")

    db.commit()


async def execute_campaign(campaign_id: int) -> None:
    """Entry point: execute a campaign end-to-end. Opens its own session."""
    db = SessionLocal()
    try:
        campaign = db.get(Campaign, campaign_id)
        if campaign is None:
            logger.error("execute_campaign: campaign %s not found", campaign_id)
            return
        if campaign.status not in {
            CampaignStatus.APPROVED.value,
            CampaignStatus.SCHEDULED.value,
            CampaignStatus.SENDING.value,
        }:
            logger.warning("Campaign %s not in a sendable state (%s)", campaign_id, campaign.status)
            return

        campaign.status = CampaignStatus.SENDING.value
        campaign.started_at = _utcnow()
        db.commit()

        factory = get_provider_factory(db)
        audience = _resolve_audience(db, campaign)
        logger.info("Campaign %s: sending to %s contacts", campaign_id, len(audience))

        # Determine the (channel, template) plan: steps for multi-channel/drip, else single.
        if campaign.steps:
            plan = [(s.channel, s.template_id, s.id, s.delay_hours) for s in campaign.steps]
        else:
            plan = [(campaign.channel, campaign.template_id, None, 0)]

        batch_size = settings.EXECUTION_BATCH_SIZE
        for channel, template_id, step_id, delay_hours in plan:
            # TODO(drip): honor delay_hours by scheduling future steps instead of
            # sending immediately. For now steps send sequentially.
            template = db.get(Template, template_id) if template_id else None
            for i in range(0, len(audience), batch_size):
                batch = audience[i : i + batch_size]
                for contact in batch:
                    # Re-check campaign not paused/cancelled mid-flight.
                    db.refresh(campaign)
                    if campaign.status in {CampaignStatus.PAUSED.value, CampaignStatus.CANCELLED.value}:
                        logger.info("Campaign %s halted (%s)", campaign_id, campaign.status)
                        return
                    await _send_one(db, factory, campaign, contact, template, channel, step_id)
                # Yield between batches (cooperative scheduling / basic rate limiting).
                await asyncio.sleep(0)

        campaign.status = CampaignStatus.COMPLETED.value
        campaign.completed_at = _utcnow()
        db.commit()
        logger.info("Campaign %s completed", campaign_id)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Campaign %s failed: %s", campaign_id, exc)
        campaign = db.get(Campaign, campaign_id)
        if campaign:
            campaign.status = CampaignStatus.FAILED.value
            db.commit()
    finally:
        db.close()
