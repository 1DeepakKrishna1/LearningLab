"""The workflow DAG executor.

Round-based scheduler that:
  * validates the graph is a DAG,
  * runs all currently-runnable nodes concurrently (bounded),
  * follows conditional branches (if/switch/approval) and skips dead branches,
  * applies per-node retry + timeout policies,
  * checkpoints after every node so a run can resume after pause/approval/crash,
  * suspends on approval/wait nodes and resumes from the checkpoint,
  * runs best-effort compensation for completed nodes when the run fails.

Importing this module registers all node handlers.
"""
from __future__ import annotations

import asyncio
from typing import Awaitable, Callable

from ..config import Settings
from ..domain.enums import ExecutionStatus, NodeRunStatus
from ..domain.execution import Execution, NodeRun
from ..domain.workflow import Workflow, WorkflowNode
from ..domain.common import iso
from ..logging_setup import get_logger
from .context import ExecutionContext
from .graph import validate_dag
from .nodes import actions, agents, logic, tools, triggers  # noqa: F401 (register handlers)
from .nodes.base import NodeResult, resolve_handler
from .policies import RetryPolicy, TimeoutPolicy, run_with_policies
from .services import EngineServices

logger = get_logger("engine.executor")

SaveFn = Callable[[Execution], Awaitable[None]]


class WorkflowExecutor:
    def __init__(self, services: EngineServices, settings: Settings,
                 save: SaveFn | None = None) -> None:
        self._services = services
        self._settings = settings
        self._save = save or (lambda _e: _noop())

    async def run(self, workflow: Workflow, execution: Execution) -> Execution:
        """Execute (or resume) a workflow run to its next stopping point."""
        validate_dag(workflow)

        ctx = ExecutionContext(variables={**workflow.variables, **execution.variables},
                               trigger=execution.trigger.model_dump())
        ctx.node_outputs = dict(execution.checkpoint.node_outputs)

        completed: set[str] = set(execution.checkpoint.completed_nodes)
        skipped: set[str] = set(execution.checkpoint.skipped_nodes)
        controls: dict[str, str] = dict(execution.checkpoint.controls)

        execution.status = ExecutionStatus.RUNNING
        execution.started_at = execution.started_at or iso()
        execution.touch()
        await self._save(execution)
        await self._services.emit_event("execution.started",
                                        {"execution_id": execution.id,
                                         "workflow_id": workflow.id})

        try:
            terminal = await self._loop(workflow, execution, ctx, completed, skipped, controls)
        except Exception as exc:  # noqa: BLE001
            logger.exception("Execution %s crashed", execution.id)
            execution.status = ExecutionStatus.FAILED
            execution.error = str(exc)
            execution.finished_at = iso()
            await self._save(execution)
            return execution

        if terminal is not None:
            return terminal

        # All reachable nodes resolved → completed.
        execution.status = ExecutionStatus.COMPLETED
        execution.result = ctx.node_outputs
        execution.finished_at = iso()
        execution.touch()
        await self._save(execution)
        await self._services.emit_event("execution.completed", {"execution_id": execution.id})
        await self._services.write_audit(actor="system", action="workflow_run",
                                          result="success", execution_id=execution.id,
                                          workflow=workflow.name)
        return execution

    # --- scheduling loop ---
    async def _loop(self, workflow: Workflow, execution: Execution, ctx: ExecutionContext,
                    completed: set[str], skipped: set[str],
                    controls: dict[str, str]) -> Execution | None:
        all_ids = {n.id for n in workflow.nodes}
        while len(completed | skipped) < len(all_ids):
            runnable: list[WorkflowNode] = []
            progressed = False

            for node in workflow.nodes:
                if node.id in completed or node.id in skipped:
                    continue
                incoming = workflow.incoming(node.id)
                if not self._all_resolved(incoming, completed, skipped):
                    continue
                taken = self._taken_sources(incoming, completed, controls)
                if not incoming or taken:
                    runnable.append(node)
                else:
                    # All predecessors resolved but none routed here → dead branch.
                    skipped.add(node.id)
                    self._record(execution, node, NodeRunStatus.SKIPPED)
                    progressed = True

            if not runnable:
                if progressed:
                    await self._checkpoint(execution, completed, skipped, controls, ctx)
                    continue
                break  # nothing left to do

            results = await asyncio.gather(
                *(self._execute_node(workflow, n, ctx, execution, completed, controls)
                  for n in runnable[: self._settings.max_parallel_nodes])
            )

            for node, result in zip(runnable, results):
                if result.status == "waiting":
                    return await self._suspend(workflow, execution, node, result,
                                               completed, skipped, controls, ctx)
                if result.status == "failed":
                    return await self._fail(workflow, execution, node, result,
                                            completed, controls, ctx)
                # completed
                completed.add(node.id)
                if result.control is not None:
                    controls[node.id] = result.control
                ctx.set_output(node.id, result.output)

            await self._checkpoint(execution, completed, skipped, controls, ctx)

        return None

    # --- node execution with policies ---
    async def _execute_node(self, workflow: Workflow, node: WorkflowNode,
                            ctx: ExecutionContext, execution: Execution,
                            completed: set[str], controls: dict[str, str]) -> NodeResult:
        handler = resolve_handler(node.type)
        if handler is None:
            return NodeResult.fail(f"No handler for node type '{node.type}'.")

        # Inject merge predecessors.
        if node.type == "logic.merge":
            sources = [e.source for e in workflow.incoming(node.id)
                       if e.source in completed]
            node.data.config = {**(node.data.config or {}), "_sources": sources}

        run = self._record(execution, node, NodeRunStatus.RUNNING, started=True)
        await self._services.emit_event("node.started",
                                        {"execution_id": execution.id, "node_id": node.id,
                                         "type": node.type})

        cfg = node.data.config or {}
        retry = RetryPolicy(max_retries=int(cfg.get("max_retries", self._settings.default_max_retries)))
        timeout = TimeoutPolicy(seconds=cfg.get("timeout", self._settings.default_node_timeout))

        def factory():
            return handler.execute(node, ctx, self._services, execution)

        run.attempts = 0

        def _on_retry(attempt: int, _exc: Exception) -> None:
            run.attempts = attempt

        try:
            result: NodeResult = await run_with_policies(factory, retry, timeout, _on_retry)
        except Exception as exc:  # noqa: BLE001
            result = NodeResult.fail(str(exc))

        run.attempts = max(run.attempts, 1)
        run.status = {
            "completed": NodeRunStatus.COMPLETED,
            "failed": NodeRunStatus.FAILED,
            "waiting": NodeRunStatus.WAITING,
            "skipped": NodeRunStatus.SKIPPED,
        }.get(result.status, NodeRunStatus.COMPLETED)
        run.output = result.output or None
        run.error = result.error
        run.finished_at = iso()
        await self._services.emit_event("node.finished",
                                        {"execution_id": execution.id, "node_id": node.id,
                                         "status": result.status})
        return result

    # --- suspend / fail / compensation ---
    async def _suspend(self, workflow: Workflow, execution: Execution, node: WorkflowNode,
                       result: NodeResult, completed: set[str], skipped: set[str],
                       controls: dict[str, str], ctx: ExecutionContext) -> Execution:
        reason = (result.suspend or {}).get("reason", "wait")
        execution.status = (ExecutionStatus.WAITING_APPROVAL if reason == "approval"
                            else ExecutionStatus.PAUSED)
        execution.checkpoint.pending_node = node.id
        await self._checkpoint(execution, completed, skipped, controls, ctx)
        logger.info("Execution %s suspended at %s (%s)", execution.id, node.id, reason)
        await self._services.emit_event("execution.suspended",
                                        {"execution_id": execution.id, "node_id": node.id,
                                         "reason": reason, "detail": result.suspend})
        return execution

    async def _fail(self, workflow: Workflow, execution: Execution, node: WorkflowNode,
                    result: NodeResult, completed: set[str], controls: dict[str, str],
                    ctx: ExecutionContext) -> Execution:
        execution.status = ExecutionStatus.FAILED
        execution.error = f"Node '{node.id}' failed: {result.error}"
        execution.finished_at = iso()
        await self._compensate(workflow, execution, completed, ctx)
        await self._save(execution)
        await self._services.emit_event("execution.failed",
                                        {"execution_id": execution.id, "node_id": node.id,
                                         "error": result.error})
        await self._services.write_audit(actor="system", action="workflow_run",
                                          result="error", execution_id=execution.id,
                                          workflow=workflow.name, detail={"node": node.id})
        return execution

    async def _compensate(self, workflow: Workflow, execution: Execution,
                          completed: set[str], ctx: ExecutionContext) -> None:
        """Best-effort: run each completed node's `config.compensation` in reverse order."""
        for node in reversed(workflow.nodes):
            if node.id not in completed:
                continue
            comp = (node.data.config or {}).get("compensation")
            if not comp or not isinstance(comp, dict):
                continue
            tool_id = comp.get("tool")
            if not tool_id:
                continue
            try:
                inputs = ctx.interpolate(comp.get("inputs", {}))
                await self._services.registry.execute(
                    self._services.registry.normalise_id(tool_id), inputs)
                logger.info("Compensated node %s via %s", node.id, tool_id)
            except Exception:  # noqa: BLE001
                logger.exception("Compensation failed for node %s", node.id)

    # --- helpers ---
    @staticmethod
    def _all_resolved(incoming, completed: set[str], skipped: set[str]) -> bool:
        return all(e.source in completed or e.source in skipped for e in incoming)

    @staticmethod
    def _taken_sources(incoming, completed: set[str], controls: dict[str, str]) -> list[str]:
        taken: list[str] = []
        for e in incoming:
            if e.source not in completed:
                continue
            ctrl = controls.get(e.source)
            if e.sourceHandle is None or ctrl is None or e.sourceHandle == ctrl:
                taken.append(e.source)
        return taken

    def _record(self, execution: Execution, node: WorkflowNode, status: NodeRunStatus,
                started: bool = False) -> NodeRun:
        run = execution.node_run(node.id)
        if run is None:
            run = NodeRun(node_id=node.id, node_type=node.type, label=node.data.label)
            execution.node_runs.append(run)
        run.status = status
        if started:
            run.started_at = iso()
        return run

    async def _checkpoint(self, execution: Execution, completed: set[str], skipped: set[str],
                          controls: dict[str, str], ctx: ExecutionContext) -> None:
        execution.checkpoint.completed_nodes = sorted(completed)
        execution.checkpoint.skipped_nodes = sorted(skipped)
        execution.checkpoint.controls = dict(controls)
        execution.checkpoint.node_outputs = dict(ctx.node_outputs)
        execution.touch()
        await self._save(execution)


async def _noop() -> None:
    return None
