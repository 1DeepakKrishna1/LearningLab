"""Generic inbound webhook → workflow trigger.

POST /api/webhooks/{workflow_id} starts a run with the JSON body as the trigger
payload. Intended for HTTP / Webhook / external-event triggers. Unauthenticated by
design (secured by the unguessable workflow id / future signing secret).
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from ..deps import ContainerDep

router = APIRouter(tags=["webhooks"])


@router.post("/webhooks/{workflow_id}")
async def trigger(workflow_id: str, request: Request, container: ContainerDep) -> dict:
    try:
        payload = await request.json()
    except Exception:  # noqa: BLE001
        payload = {}
    try:
        execution = await container.execution_service.start(
            workflow_id, trigger_type="webhook", payload=payload, created_by="webhook")
    except KeyError as exc:
        raise HTTPException(404, str(exc)) from exc
    return {"execution_id": execution.id, "status": execution.status.value}
