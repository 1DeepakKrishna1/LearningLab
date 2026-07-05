"""Health and configuration-status endpoint."""
from __future__ import annotations

from fastapi import APIRouter

from ..config import get_settings
from .. import __version__

router = APIRouter(tags=["health"])


@router.get("/api/health")
async def health() -> dict:
    settings = get_settings()
    return {
        "status": "ok",
        "version": __version__,
        "llm_configured": bool(settings.openai_api_key),
        "model": settings.openai_model,
        "approval_required_methods": settings.approval_required_methods,
    }
