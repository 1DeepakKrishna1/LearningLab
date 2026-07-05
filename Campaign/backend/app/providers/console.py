"""Console / sandbox adapters.

These are the default, safe providers for self-hosted local use: they log the
message instead of sending it and report a small set of *synthetic* downstream
events so analytics dashboards have realistic data without external calls.
"""
from __future__ import annotations

import logging
import uuid

from app.providers.base import EmailProvider, Message, ProviderResult, PushProvider, SmsProvider

logger = logging.getLogger("app.providers.console")


def _synthetic_email_events() -> list[str]:
    # Deterministic-ish funnel for demo dashboards.
    return ["delivered", "opened", "clicked"]


class ConsoleEmailProvider(EmailProvider):
    async def send(self, message: Message) -> ProviderResult:
        logger.info("[console-email] to=%s subject=%s", message.to, message.subject)
        return ProviderResult(
            success=True,
            message_id=f"console-{uuid.uuid4().hex}",
            synthetic_events=_synthetic_email_events(),
        )

    async def health_check(self) -> tuple[bool, str]:
        return True, "console adapter always healthy"


class ConsoleSmsProvider(SmsProvider):
    async def send(self, message: Message) -> ProviderResult:
        logger.info("[console-sms] to=%s body=%s", message.to, message.body[:40])
        return ProviderResult(
            success=True,
            message_id=f"console-{uuid.uuid4().hex}",
            synthetic_events=["delivered"],
        )

    async def health_check(self) -> tuple[bool, str]:
        return True, "console adapter always healthy"


class ConsolePushProvider(PushProvider):
    async def send(self, message: Message) -> ProviderResult:
        logger.info("[console-push] to=%s title=%s", message.to, message.title)
        return ProviderResult(
            success=True,
            message_id=f"console-{uuid.uuid4().hex}",
            synthetic_events=["delivered", "opened"],
        )

    async def health_check(self) -> tuple[bool, str]:
        return True, "console adapter always healthy"
