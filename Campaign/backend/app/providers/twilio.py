"""Twilio SMS provider (REST API via httpx; sandbox unless live creds present)."""
from __future__ import annotations

import logging
import uuid

import httpx

from app.providers.base import Message, ProviderResult, SmsProvider

logger = logging.getLogger("app.providers.twilio")


class TwilioSmsProvider(SmsProvider):
    async def send(self, message: Message) -> ProviderResult:
        sid = self.config.get("account_sid")
        token = self.config.get("auth_token")
        from_number = self.config.get("from_number")
        if self.mode != "live" or not (sid and token and from_number):
            logger.info("[twilio:sandbox] to=%s body=%s", message.to, message.body[:40])
            return ProviderResult(
                success=True,
                message_id=f"tw-sandbox-{uuid.uuid4().hex}",
                synthetic_events=["delivered"],
            )
        url = f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json"
        data = {"To": message.to, "From": from_number, "Body": message.body}
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.post(url, data=data, auth=(sid, token))
            if resp.status_code in (200, 201):
                return ProviderResult(success=True, message_id=resp.json().get("sid"))
            return ProviderResult(success=False, error=f"HTTP {resp.status_code}: {resp.text[:200]}")
        except Exception as exc:  # noqa: BLE001
            return ProviderResult(success=False, error=str(exc))

    async def health_check(self) -> tuple[bool, str]:
        if self.mode != "live" or not self.config.get("account_sid"):
            return True, "sandbox mode"
        return True, "credentials present"  # TODO: GET account resource for a real check
