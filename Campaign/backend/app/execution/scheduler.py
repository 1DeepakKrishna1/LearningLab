"""Background scheduler loop.

Polls for campaigns whose ``scheduled_at``/``next_run_at`` is due and launches
execution. Recurring campaigns compute their next run after each fire. Runs as a
single asyncio task started on app startup.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import or_, select

from app.core.config import settings
from app.core.database import SessionLocal
from app.execution.engine import execute_campaign
from app.models import Campaign
from app.models.enums import CampaignStatus

logger = logging.getLogger("app.execution.scheduler")

_FREQ_DELTA = {
    "DAILY": lambda i: timedelta(days=i),
    "WEEKLY": lambda i: timedelta(weeks=i),
    "HOURLY": lambda i: timedelta(hours=i),
}


def _compute_next_run(recurrence: dict, frm: datetime) -> datetime | None:
    freq = (recurrence or {}).get("freq", "DAILY").upper()
    interval = int((recurrence or {}).get("interval", 1))
    delta_fn = _FREQ_DELTA.get(freq)
    if freq == "MONTHLY":
        return frm + timedelta(days=30 * interval)  # simplified month handling
    if delta_fn is None:
        return None
    return frm + delta_fn(interval)


async def _tick() -> None:
    db = SessionLocal()
    try:
        # Naive UTC to match SQLite-stored (tz-stripped) campaign datetimes.
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        due = db.scalars(
            select(Campaign).where(
                Campaign.status == CampaignStatus.SCHEDULED.value,
                or_(
                    Campaign.scheduled_at <= now,
                    Campaign.next_run_at <= now,
                ),
            )
        ).all()
        for campaign in due:
            logger.info("Scheduler firing campaign %s", campaign.id)
            recurrence = campaign.recurrence
            # Launch execution as a background task.
            asyncio.create_task(execute_campaign(campaign.id))
            if recurrence:
                # Recurring: schedule next occurrence and keep status scheduled.
                next_run = _compute_next_run(recurrence, now)
                count = recurrence.get("count")
                fired = recurrence.get("_fired", 0) + 1
                recurrence["_fired"] = fired
                if next_run and (count is None or fired < count):
                    campaign.next_run_at = next_run
                    campaign.recurrence = dict(recurrence)
                else:
                    campaign.next_run_at = None
                db.commit()
    except Exception as exc:  # noqa: BLE001
        logger.exception("Scheduler tick error: %s", exc)
    finally:
        db.close()


async def scheduler_loop(stop_event: asyncio.Event) -> None:
    logger.info("Scheduler started (poll=%ss)", settings.SCHEDULER_POLL_SECONDS)
    while not stop_event.is_set():
        await _tick()
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=settings.SCHEDULER_POLL_SECONDS)
        except asyncio.TimeoutError:
            continue
    logger.info("Scheduler stopped")
