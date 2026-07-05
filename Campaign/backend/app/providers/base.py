"""Provider abstractions (Adapter pattern).

Every concrete provider implements one of the channel ABCs and returns a
uniform :class:`ProviderResult`, so the execution engine is decoupled from any
specific vendor SDK.
"""
from __future__ import annotations

import abc
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Message:
    """A normalized outbound message handed to a provider."""

    to: str  # email address, phone number, or device token
    subject: str | None = None
    body: str = ""
    html: str | None = None
    # Push-specific
    title: str | None = None
    image_url: str | None = None
    deep_link: str | None = None
    buttons: list[dict[str, Any]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ProviderResult:
    success: bool
    message_id: str | None = None
    error: str | None = None
    # Events the provider can synchronously report (console adapter simulates these).
    synthetic_events: list[str] = field(default_factory=list)


class BaseProvider(abc.ABC):
    channel: str = ""

    def __init__(self, name: str, config: dict[str, Any], mode: str = "console") -> None:
        self.name = name
        self.config = config or {}
        self.mode = mode

    @abc.abstractmethod
    async def send(self, message: Message) -> ProviderResult:  # pragma: no cover - interface
        ...

    @abc.abstractmethod
    async def health_check(self) -> tuple[bool, str]:  # pragma: no cover - interface
        """Return (healthy, detail)."""
        ...


class EmailProvider(BaseProvider):
    channel = "email"


class SmsProvider(BaseProvider):
    channel = "sms"


class PushProvider(BaseProvider):
    channel = "push"
