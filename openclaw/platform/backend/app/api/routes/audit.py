"""Audit log routes."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from ...domain.audit import AuditEntry
from ..deps import ContainerDep, require

router = APIRouter(tags=["audit"])


@router.get("/audit", response_model=list[AuditEntry],
            dependencies=[Depends(require("audit:read"))])
async def list_audit(container: ContainerDep, limit: int = 200) -> list[AuditEntry]:
    return await container.audit_service.list(limit)
