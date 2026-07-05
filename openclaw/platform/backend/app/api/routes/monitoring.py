"""Monitoring / dashboard routes."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from ..deps import ContainerDep, require

router = APIRouter(tags=["monitoring"])


@router.get("/monitoring/dashboard", dependencies=[Depends(require("monitoring:read"))])
async def dashboard(container: ContainerDep) -> dict:
    return await container.monitoring_service.dashboard()


@router.get("/monitoring/timeline", dependencies=[Depends(require("monitoring:read"))])
async def timeline(container: ContainerDep, limit: int = 50) -> list[dict]:
    return await container.monitoring_service.timeline(limit)
