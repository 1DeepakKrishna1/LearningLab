"""Concrete messaging providers.

* ConsoleProvider — logs messages; the default, needs no credentials (great for dev/tests).
* MetaWhatsAppProvider — WhatsApp Business Cloud API (Meta Graph).
* TwilioProvider — Twilio WhatsApp.
* Telegram/Teams/Slack — declared as future stubs to show the extension point.

All network providers fail soft (return SendResult(success=False)) when unconfigured.
"""
from __future__ import annotations

import os
from typing import Any

from ..logging_setup import get_logger
from .base import InboundMessage, MessagingProvider, SendResult

logger = get_logger("messaging")


class ConsoleProvider(MessagingProvider):
    name = "console"

    async def send(self, to: str, text: str, **kwargs: Any) -> SendResult:
        logger.info("[console-message] to=%s | %s", to, text)
        return SendResult(success=True, provider=self.name, message_id="console")

    def parse_inbound(self, payload: dict[str, Any]) -> InboundMessage | None:
        sender = payload.get("from") or payload.get("sender")
        text = payload.get("text") or payload.get("body")
        if not sender or text is None:
            return None
        return InboundMessage(sender=sender, text=str(text), provider=self.name, raw=payload)


class MetaWhatsAppProvider(MessagingProvider):
    name = "meta"

    def __init__(self) -> None:
        self._token = os.getenv("META_WHATSAPP_TOKEN", "")
        self._phone_id = os.getenv("META_PHONE_NUMBER_ID", "")

    async def send(self, to: str, text: str, **kwargs: Any) -> SendResult:
        if not self._token or not self._phone_id:
            logger.warning("Meta WhatsApp not configured; message dropped.")
            return SendResult(success=False, provider=self.name, detail={"reason": "unconfigured"})
        import httpx
        url = f"https://graph.facebook.com/v19.0/{self._phone_id}/messages"
        body = {"messaging_product": "whatsapp", "to": to,
                "type": "text", "text": {"body": text}}
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.post(url, json=body,
                                     headers={"Authorization": f"Bearer {self._token}"})
        ok = resp.status_code < 300
        return SendResult(success=ok, provider=self.name,
                          detail={"status": resp.status_code, "body": resp.text[:500]})

    def parse_inbound(self, payload: dict[str, Any]) -> InboundMessage | None:
        try:
            value = payload["entry"][0]["changes"][0]["value"]
            msg = value["messages"][0]
            return InboundMessage(sender=msg["from"], text=msg["text"]["body"],
                                  provider=self.name, raw=payload)
        except (KeyError, IndexError, TypeError):
            return None


class TwilioProvider(MessagingProvider):
    name = "twilio"

    def __init__(self) -> None:
        self._sid = os.getenv("TWILIO_ACCOUNT_SID", "")
        self._token = os.getenv("TWILIO_AUTH_TOKEN", "")
        self._from = os.getenv("TWILIO_WHATSAPP_FROM", "")

    async def send(self, to: str, text: str, **kwargs: Any) -> SendResult:
        if not self._sid or not self._token or not self._from:
            logger.warning("Twilio not configured; message dropped.")
            return SendResult(success=False, provider=self.name, detail={"reason": "unconfigured"})
        import httpx
        url = f"https://api.twilio.com/2010-04-01/Accounts/{self._sid}/Messages.json"
        to_addr = to if to.startswith("whatsapp:") else f"whatsapp:{to}"
        data = {"From": self._from, "To": to_addr, "Body": text}
        async with httpx.AsyncClient(timeout=20, auth=(self._sid, self._token)) as client:
            resp = await client.post(url, data=data)
        ok = resp.status_code < 300
        return SendResult(success=ok, provider=self.name, detail={"status": resp.status_code})

    def parse_inbound(self, payload: dict[str, Any]) -> InboundMessage | None:
        sender = payload.get("From", "").replace("whatsapp:", "")
        text = payload.get("Body")
        if not sender or text is None:
            return None
        return InboundMessage(sender=sender, text=str(text), provider=self.name, raw=payload)
