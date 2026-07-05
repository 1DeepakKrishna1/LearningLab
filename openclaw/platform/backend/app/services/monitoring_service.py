"""Monitoring / dashboard aggregation service."""
from __future__ import annotations

from typing import Any

from ..agents.runtime import AgentRuntimeManager
from ..domain.enums import ExecutionStatus
from ..domain.execution import Execution
from ..registry.tool_registry import ToolRegistry
from ..storage.repository import Repository


class MonitoringService:
    def __init__(self, execution_repo: Repository[Execution],
                 registry: ToolRegistry, agent_runtime: AgentRuntimeManager,
                 running_count_fn) -> None:
        self._executions = execution_repo
        self._registry = registry
        self._agent_runtime = agent_runtime
        self._running_count_fn = running_count_fn

    async def dashboard(self) -> dict[str, Any]:
        execs = await self._executions.list()
        by_status: dict[str, int] = {}
        for e in execs:
            by_status[e.status.value] = by_status.get(e.status.value, 0) + 1

        tool_usage: dict[str, int] = {}
        for e in execs:
            for run in e.node_runs:
                if run.node_type.startswith("tool."):
                    key = run.node_type
                    tool_usage[key] = tool_usage.get(key, 0) + 1

        return {
            "executions": {
                "total": len(execs),
                "running": by_status.get(ExecutionStatus.RUNNING.value, 0),
                "completed": by_status.get(ExecutionStatus.COMPLETED.value, 0),
                "failed": by_status.get(ExecutionStatus.FAILED.value, 0),
                "waiting_approval": by_status.get(ExecutionStatus.WAITING_APPROVAL.value, 0),
                "by_status": by_status,
            },
            "queue_depth": self._running_count_fn(),
            "active_agents": self._agent_runtime.active_count,
            "active_agent_names": self._agent_runtime.active_agents(),
            "tools": {"registered": len(self._registry.all()),
                      "categories": len(self._registry.by_category())},
            "tool_usage": sorted(tool_usage.items(), key=lambda kv: kv[1], reverse=True)[:10],
        }

    async def timeline(self, limit: int = 50) -> list[dict[str, Any]]:
        execs = await self._executions.list()
        execs.sort(key=lambda e: e.created_at, reverse=True)
        return [
            {"execution_id": e.id, "workflow": e.workflow_name, "status": e.status.value,
             "started_at": e.started_at, "finished_at": e.finished_at,
             "nodes": len(e.node_runs)}
            for e in execs[:limit]
        ]
