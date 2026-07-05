"""Audit logging service."""
from __future__ import annotations

from typing import Any

from ..domain.audit import AuditEntry
from ..domain.enums import AuditActor
from ..storage.repository import Repository


class AuditService:
    def __init__(self, repo: Repository[AuditEntry]) -> None:
        self._repo = repo

    async def log(self, *, action: str, actor: str | AuditActor = AuditActor.SYSTEM,
                  result: str = "success", actor_id: str | None = None,
                  workflow: str | None = None, agent: str | None = None,
                  execution_id: str | None = None,
                  detail: dict[str, Any] | None = None) -> AuditEntry:
        entry = AuditEntry(
            actor=AuditActor(actor) if isinstance(actor, str) else actor,
            actor_id=actor_id, workflow=workflow, agent=agent,
            execution_id=execution_id, action=action, result=result,
            detail=detail or {},
        )
        await self._repo.add(entry)
        return entry

    async def list(self, limit: int = 200) -> list[AuditEntry]:
        entries = await self._repo.list()
        entries.sort(key=lambda e: e.timestamp, reverse=True)
        return entries[:limit]
