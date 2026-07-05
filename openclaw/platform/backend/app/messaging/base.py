"""Messaging provider abstraction.

A single ``MessagingProvider`` interface lets WhatsApp (Meta), Twilio, and future
channels (Telegram/Teams/Slack) be plugged in without touching call sites. Inbound
messages are normalised to :class:`InboundMessage` regardless of provider.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class InboundMessage:
    sender: str
    text: str
    provider: str
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class SendResult:
    success: bool
    provider: str
    message_id: str | None = None
    detail: dict[str, Any] = field(default_factory=dict)


class MessagingProvider(ABC):
    """Abstract outbound/inbound messaging channel."""

    name: str = "base"

    @abstractmethod
    async def send(self, to: str, text: str, **kwargs: Any) -> SendResult:
        """Send a text message to a recipient."""

    @abstractmethod
    def parse_inbound(self, payload: dict[str, Any]) -> InboundMessage | None:
        """Normalise a provider-specific webhook payload into an InboundMessage."""
