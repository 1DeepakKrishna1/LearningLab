"""Resolve the configured messaging provider."""
from __future__ import annotations

from ..config import Settings
from .base import MessagingProvider
from .providers import ConsoleProvider, MetaWhatsAppProvider, TwilioProvider

_PROVIDERS = {
    "console": ConsoleProvider,
    "meta": MetaWhatsAppProvider,
    "twilio": TwilioProvider,
}


def build_messaging_provider(settings: Settings) -> MessagingProvider:
    cls = _PROVIDERS.get(settings.messaging_provider, ConsoleProvider)
    return cls()
