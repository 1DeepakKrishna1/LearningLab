"""Execution service — launches, resumes, cancels and tracks workflow runs."""
from __future__ import annotations

import asyncio
from typing import Any

from ..config import Settings
from ..domain.common import iso
from ..domain.enums import ExecutionStatus
from ..domain.execution import Execution, TriggerInfo
from ..domain.workflow import Workflow
from ..engine.executor import WorkflowExecutor
from ..engine.services import EngineServices
from ..logging_setup import get_logger
from ..storage.repository import Repository

logger = get_logger("service.execution")


class ExecutionService:
    def __init__(self, settings: Settings, engine_services: EngineServices,
                 workflow_repo: Repository[Workflow],
                 execution_repo: Repository[Execution]) -> None:
        self._settings = settings
        self._engine_services = engine_services
        self._workflows = workflow_repo
        self._executions = execution_repo
        self._tasks: dict[str, asyncio.Task] = {}

    # --- persistence callback for the executor ---
    async def _save(self, execution: Execution) -> None:
        await self._executions.upsert(execution)  # type: ignore[attr-defined]

    def _executor(self) -> WorkflowExecutor:
        return WorkflowExecutor(self._engine_services, self._settings, self._save)

    # --- public API ---
    async def start(self, workflow_id: str, trigger_type: str = "manual",
                    payload: dict[str, Any] | None = None,
                    variables: dict[str, Any] | None = None,
                    created_by: str | None = None) -> Execution:
        workflow = await self._workflows.get(workflow_id)
        if not workflow:
            raise KeyError(f"Workflow '{workflow_id}' not found.")
        execution = Execution(
            workflow_id=workflow.id,
            workflow_version=workflow.version,
            workflow_name=workflow.name,
            trigger=TriggerInfo(type=trigger_type, payload=payload or {}),
            variables=variables or {},
            created_by=created_by,
        )
        await self._executions.add(execution)
        self._launch(workflow, execution)
        return execution

    async def resume(self, execution_id: str) -> Execution | None:
        execution = await self._executions.get(execution_id)
        if not execution:
            return None
        workflow = await self._workflows.get(execution.workflow_id)
        if not workflow:
            return None
        if execution.status.is_terminal:
            return execution
        self._launch(workflow, execution)
        return execution

    async def cancel(self, execution_id: str) -> Execution | None:
        execution = await self._executions.get(execution_id)
        if not execution:
            return None
        task = self._tasks.get(execution_id)
        if task and not task.done():
            task.cancel()
        execution.status = ExecutionStatus.CANCELLED
        execution.finished_at = iso()
        execution.touch()
        await self._executions.update(execution)
        return execution

    async def get(self, execution_id: str) -> Execution | None:
        return await self._executions.get(execution_id)

    async def list(self, workflow_id: str | None = None,
                   status: str | None = None) -> list[Execution]:
        items = await self._executions.list()
        if workflow_id:
            items = [e for e in items if e.workflow_id == workflow_id]
        if status:
            items = [e for e in items if e.status.value == status]
        items.sort(key=lambda e: e.created_at, reverse=True)
        return items

    # --- background launch ---
    def _launch(self, workflow: Workflow, execution: Execution) -> None:
        async def _runner() -> None:
            try:
                await self._executor().run(workflow, execution)
            except asyncio.CancelledError:
                logger.info("Execution %s cancelled", execution.id)
            except Exception:  # noqa: BLE001
                logger.exception("Execution %s runner crashed", execution.id)
            finally:
                self._tasks.pop(execution.id, None)

        self._tasks[execution.id] = asyncio.create_task(_runner())

    @property
    def running_count(self) -> int:
        return sum(1 for t in self._tasks.values() if not t.done())
