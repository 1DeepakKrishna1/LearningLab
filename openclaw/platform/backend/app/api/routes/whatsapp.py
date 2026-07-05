"""WhatsApp integration routes (provider-agnostic webhook + verification).

Inbound messages are normalised by the configured provider, routed through the
chatbot service, and the reply is sent back over the same channel. Approval
keywords (APPROVE/REJECT <id>) are handled directly.
"""
from __future__ import annotations

import re

from fastapi import APIRouter, Request
from fastapi.responses import PlainTextResponse

from ...domain.approval import ApprovalDecision
from ...domain.enums import ApprovalStatus
from ...logging_setup import get_logger
from ..deps import ContainerDep

router = APIRouter(tags=["whatsapp"])
logger = get_logger("api.whatsapp")

_APPROVE = re.compile(r"\b(approve|reject)\b\s+([0-9a-f]{8,})", re.IGNORECASE)


@router.get("/whatsapp/webhook")
async def verify(request: Request) -> PlainTextResponse:
    """Meta webhook verification handshake."""
    params = request.query_params
    challenge = params.get("hub.challenge", "")
    return PlainTextResponse(challenge)


@router.post("/whatsapp/webhook")
async def inbound(request: Request, container: ContainerDep) -> dict:
    payload = await request.json()
    provider = container.messaging
    message = provider.parse_inbound(payload)
    if not message:
        return {"status": "ignored"}

    text = message.text.strip()
    # Approval shortcut.
    approve_match = _APPROVE.search(text)
    if approve_match:
        verb, approval_id = approve_match.group(1).lower(), approve_match.group(2)
        decision = ApprovalStatus.APPROVED if verb == "approve" else ApprovalStatus.REJECTED
        try:
            await container.approval_service.decide(
                ApprovalDecision(approval_id=approval_id, decision=decision),
                decided_by=f"whatsapp:{message.sender}")
            await provider.send(message.sender, f"Recorded: {verb} for {approval_id}.")
        except Exception as exc:  # noqa: BLE001
            await provider.send(message.sender, f"Could not process approval: {exc}")
        return {"status": "approval_processed"}

    # Otherwise treat as a chatbot command.
    result = await container.chatbot_service.chat(text, user_id=f"whatsapp:{message.sender}")
    await provider.send(message.sender, result.get("reply", "Done."))
    return {"status": "ok", "action": result.get("action")}
