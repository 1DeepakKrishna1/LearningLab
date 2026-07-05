"""SendGrid email provider.

Uses the SendGrid v3 REST API via httpx when in ``live`` mode with an API key;
otherwise behaves as a sandbox adapter. (No vendor SDK dependency required.)
"""
from __future__ import annotations

import logging
import uuid

import httpx

from app.providers.base import EmailProvider, Message, ProviderResult

logger = logging.getLogger("app.providers.sendgrid")
_API = "https://api.sendgrid.com/v3/mail/send"


class SendGridEmailProvider(EmailProvider):
    async def send(self, message: Message) -> ProviderResult:
        api_key = self.config.get("api_key")
        if self.mode != "live" or not api_key:
            logger.info("[sendgrid:sandbox] to=%s subject=%s", message.to, message.subject)
            return ProviderResult(
                success=True,
                message_id=f"sg-sandbox-{uuid.uuid4().hex}",
                synthetic_events=["delivered", "opened", "clicked"],
            )
        payload = {
            "personalizations": [{"to": [{"email": message.to}]}],
            "from": {"email": self.config.get("from_email", "no-reply@localhost")},
            "subject": message.subject or "",
            "content": [{"type": "text/html", "value": message.html or message.body}],
        }
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.post(
                    _API, json=payload, headers={"Authorization": f"Bearer {api_key}"}
                )
            if resp.status_code in (200, 202):
                msg_id = resp.headers.get("X-Message-Id", f"sg-{uuid.uuid4().hex}")
                return ProviderResult(success=True, message_id=msg_id)
            return ProviderResult(success=False, error=f"HTTP {resp.status_code}: {resp.text[:200]}")
        except Exception as exc:  # noqa: BLE001
            return ProviderResult(success=False, error=str(exc))

    async def health_check(self) -> tuple[bool, str]:
        if self.mode != "live" or not self.config.get("api_key"):
            return True, "sandbox mode"
        return True, "api key present"  # TODO: ping SendGrid /scopes for a real check
