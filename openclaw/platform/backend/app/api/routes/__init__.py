"""Route aggregation."""
from __future__ import annotations

from fastapi import APIRouter

from . import (
    agents,
    approvals,
    audit,
    auth,
    chatbot,
    executions,
    monitoring,
    settings,
    tools,
    webhooks,
    whatsapp,
    workflows,
)

api_router = APIRouter(prefix="/api")
api_router.include_router(auth.router)
api_router.include_router(workflows.router)
api_router.include_router(executions.router)
api_router.include_router(agents.router)
api_router.include_router(tools.router)
api_router.include_router(approvals.router)
api_router.include_router(audit.router)
api_router.include_router(monitoring.router)
api_router.include_router(chatbot.router)
api_router.include_router(whatsapp.router)
api_router.include_router(webhooks.router)
api_router.include_router(settings.router)
