"""Workflow CRUD + validation service."""
from __future__ import annotations

from ..domain.common import iso
from ..domain.enums import WorkflowStatus
from ..domain.workflow import Workflow, WorkflowCreate, WorkflowUpdate
from ..engine.graph import GraphError, validate_dag
from ..storage.repository import Repository


class WorkflowService:
    def __init__(self, repo: Repository[Workflow]) -> None:
        self._repo = repo

    async def list(self) -> list[Workflow]:
        return await self._repo.list()

    async def get(self, workflow_id: str) -> Workflow | None:
        return await self._repo.get(workflow_id)

    async def create(self, data: WorkflowCreate, created_by: str | None = None) -> Workflow:
        wf = Workflow(**data.model_dump(), created_by=created_by)
        return await self._repo.add(wf)

    async def save(self, wf: Workflow) -> Workflow:
        """Create or update a full workflow object (used by AI builder + import)."""
        existing = await self._repo.get(wf.id)
        if existing:
            wf.updated_at = iso()
            return await self._repo.update(wf)
        return await self._repo.add(wf)

    async def update(self, workflow_id: str, patch: WorkflowUpdate) -> Workflow | None:
        wf = await self._repo.get(workflow_id)
        if not wf:
            return None
        data = patch.model_dump(exclude_unset=True)
        for key, value in data.items():
            setattr(wf, key, value)
        if "status" in data:
            wf.status = WorkflowStatus(data["status"])
        wf.version += 1
        wf.updated_at = iso()
        return await self._repo.update(wf)

    async def delete(self, workflow_id: str) -> bool:
        return await self._repo.delete(workflow_id)

    async def validate(self, workflow_id: str) -> dict:
        wf = await self._repo.get(workflow_id)
        if not wf:
            return {"valid": False, "errors": ["Workflow not found."]}
        return self.validate_obj(wf)

    @staticmethod
    def validate_obj(wf: Workflow) -> dict:
        errors: list[str] = []
        try:
            validate_dag(wf)
        except GraphError as exc:
            errors.append(str(exc))
        triggers = wf.trigger_nodes()
        if not triggers:
            errors.append("Workflow has no trigger node.")
        return {"valid": not errors, "errors": errors,
                "trigger_count": len(triggers), "node_count": len(wf.nodes)}
