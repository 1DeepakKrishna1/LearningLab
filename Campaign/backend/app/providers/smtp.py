"""SMTP email provider (real send via stdlib smtplib).

Falls back to console behaviour if not in ``live`` mode or if no host configured.
"""
from __future__ import annotations

import logging
import smtplib
import uuid
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.providers.base import EmailProvider, Message, ProviderResult

logger = logging.getLogger("app.providers.smtp")


class SmtpEmailProvider(EmailProvider):
    async def send(self, message: Message) -> ProviderResult:
        host = self.config.get("host")
        if self.mode != "live" or not host:
            logger.info("[smtp:sandbox] would send to=%s subject=%s", message.to, message.subject)
            return ProviderResult(
                success=True,
                message_id=f"smtp-sandbox-{uuid.uuid4().hex}",
                synthetic_events=["delivered", "opened"],
            )
        try:
            mime = MIMEMultipart("alternative")
            mime["Subject"] = message.subject or ""
            mime["From"] = self.config.get("from_email", "no-reply@localhost")
            mime["To"] = message.to
            mime.attach(MIMEText(message.body or "", "plain"))
            if message.html:
                mime.attach(MIMEText(message.html, "html"))

            port = int(self.config.get("port", 587))
            with smtplib.SMTP(host, port, timeout=15) as server:
                if self.config.get("use_tls", True):
                    server.starttls()
                username = self.config.get("username")
                password = self.config.get("password")
                if username and password:
                    server.login(username, password)
                server.send_message(mime)
            return ProviderResult(success=True, message_id=f"smtp-{uuid.uuid4().hex}")
        except Exception as exc:  # noqa: BLE001
            logger.warning("SMTP send failed: %s", exc)
            return ProviderResult(success=False, error=str(exc))

    async def health_check(self) -> tuple[bool, str]:
        host = self.config.get("host")
        if self.mode != "live" or not host:
            return True, "sandbox mode (no real connection)"
        try:
            port = int(self.config.get("port", 587))
            with smtplib.SMTP(host, port, timeout=10) as server:
                server.noop()
            return True, f"connected to {host}:{port}"
        except Exception as exc:  # noqa: BLE001
            return False, str(exc)
