"""Provider factory: resolves the right adapter for a channel + provider type.

Implements:
- Adapter registry keyed by ProviderType
- Provider selection (per-config or channel default) and switching
- Retry-with-backoff wrapper around ``send``
- Health checks
"""
from __future__ import annotations

import asyncio
import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import load_json_file, settings
from app.models import ProviderConfig
from app.models.enums import Channel, ProviderType
from app.providers.base import BaseProvider, Message, ProviderResult
from app.providers.console import (
    ConsoleEmailProvider,
    ConsolePushProvider,
    ConsoleSmsProvider,
)
from app.providers.fcm import FcmPushProvider, OneSignalPushProvider
from app.providers.sendgrid import SendGridEmailProvider
from app.providers.smtp import SmtpEmailProvider
from app.providers.twilio import TwilioSmsProvider

logger = logging.getLogger("app.providers.factory")

# Registry: provider_type -> adapter class
_REGISTRY: dict[str, type[BaseProvider]] = {
    ProviderType.CONSOLE.value: ConsoleEmailProvider,  # overridden per channel below
    ProviderType.SMTP.value: SmtpEmailProvider,
    ProviderType.SENDGRID.value: SendGridEmailProvider,
    ProviderType.TWILIO.value: TwilioSmsProvider,
    ProviderType.FCM.value: FcmPushProvider,
    ProviderType.ONESIGNAL.value: OneSignalPushProvider,
}

# Console adapter per channel.
_CONSOLE_BY_CHANNEL: dict[str, type[BaseProvider]] = {
    Channel.EMAIL.value: ConsoleEmailProvider,
    Channel.SMS.value: ConsoleSmsProvider,
    Channel.PUSH.value: ConsolePushProvider,
}


def _merge_secret_config(provider_type: str, config: dict) -> dict:
    """Overlay secrets from data/providers/<type>.json onto the stored config."""
    file_cfg = load_json_file(f"providers/{provider_type}.json") or {}
    merged = {**file_cfg, **(config or {})}
    return merged


class ProviderFactory:
    def __init__(self, db: Session) -> None:
        self.db = db

    def build(self, pc: ProviderConfig) -> BaseProvider:
        if pc.provider_type == ProviderType.CONSOLE.value:
            cls = _CONSOLE_BY_CHANNEL.get(pc.channel, ConsoleEmailProvider)
        else:
            cls = _REGISTRY.get(pc.provider_type)
            if cls is None:
                logger.warning("Unknown provider_type %s; using console", pc.provider_type)
                cls = _CONSOLE_BY_CHANNEL.get(pc.channel, ConsoleEmailProvider)
        config = _merge_secret_config(pc.provider_type, pc.config)
        return cls(name=pc.name, config=config, mode=pc.mode)

    def get_for_channel(self, channel: str, provider_config_id: int | None = None) -> BaseProvider:
        """Resolve a provider for a channel.

        Selection order: explicit config id -> channel default -> first active ->
        built-in console fallback (so the platform always sends *something*).
        """
        stmt = select(ProviderConfig).where(
            ProviderConfig.channel == channel, ProviderConfig.is_active.is_(True)
        )
        if provider_config_id is not None:
            pc = self.db.get(ProviderConfig, provider_config_id)
            if pc:
                return self.build(pc)

        configs = list(self.db.scalars(stmt))
        default = next((c for c in configs if c.is_default), None)
        chosen = default or (configs[0] if configs else None)
        if chosen:
            return self.build(chosen)

        logger.info("No provider configured for %s; using console fallback", channel)
        cls = _CONSOLE_BY_CHANNEL.get(channel, ConsoleEmailProvider)
        return cls(name=f"console-{channel}", config={}, mode="console")

    async def send_with_retry(
        self, provider: BaseProvider, message: Message, max_retries: int | None = None
    ) -> ProviderResult:
        """Send with exponential backoff. Returns the last result on exhaustion."""
        retries = max_retries if max_retries is not None else settings.EXECUTION_MAX_RETRIES
        last: ProviderResult = ProviderResult(success=False, error="not attempted")
        for attempt in range(retries + 1):
            last = await provider.send(message)
            if last.success:
                return last
            if attempt < retries:
                await asyncio.sleep(min(2**attempt * 0.5, 8))
                logger.info("Retry %s/%s for provider %s", attempt + 1, retries, provider.name)
        return last

    async def health_check(self, pc: ProviderConfig) -> tuple[bool, str]:
        provider = self.build(pc)
        return await provider.health_check()


def get_provider_factory(db: Session) -> ProviderFactory:
    return ProviderFactory(db)
