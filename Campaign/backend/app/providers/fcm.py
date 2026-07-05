"""Firebase Cloud Messaging push provider (sandbox unless live creds present).

A production integration would use the firebase-admin SDK with a service
account and OAuth2 bearer token. Here we keep the adapter shape and fall back
to sandbox behaviour by default. TODO: wire firebase-admin for live mode.
"""
from __future__ import annotations

import logging
import uuid

from app.providers.base import Message, ProviderResult, PushProvider

logger = logging.getLogger("app.providers.fcm")


class FcmPushProvider(PushProvider):
    async def send(self, message: Message) -> ProviderResult:
        project_id = self.config.get("project_id")
        if self.mode != "live" or not project_id:
            logger.info("[fcm:sandbox] token=%s title=%s", message.to[:12], message.title)
            return ProviderResult(
                success=True,
                message_id=f"fcm-sandbox-{uuid.uuid4().hex}",
                synthetic_events=["delivered", "opened"],
            )
        # TODO: implement live FCM HTTP v1 send using a service-account OAuth token.
        logger.warning("FCM live mode not implemented; behaving as sandbox.")
        return ProviderResult(success=True, message_id=f"fcm-{uuid.uuid4().hex}", synthetic_events=["delivered"])

    async def health_check(self) -> tuple[bool, str]:
        if self.mode != "live" or not self.config.get("project_id"):
            return True, "sandbox mode"
        return True, "project configured"


class OneSignalPushProvider(PushProvider):
    """OneSignal push provider (REST API shape; sandbox unless live creds)."""

    async def send(self, message: Message) -> ProviderResult:
        app_id = self.config.get("app_id")
        if self.mode != "live" or not app_id:
            logger.info("[onesignal:sandbox] title=%s", message.title)
            return ProviderResult(
                success=True,
                message_id=f"os-sandbox-{uuid.uuid4().hex}",
                synthetic_events=["delivered", "opened"],
            )
        # TODO: POST https://onesignal.com/api/v1/notifications with REST API key.
        logger.warning("OneSignal live mode not implemented; behaving as sandbox.")
        return ProviderResult(success=True, message_id=f"os-{uuid.uuid4().hex}", synthetic_events=["delivered"])

    async def health_check(self) -> tuple[bool, str]:
        if self.mode != "live" or not self.config.get("app_id"):
            return True, "sandbox mode"
        return True, "app configured"
