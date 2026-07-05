"""Agent node handlers (openclaw / supervisor / planner / research / executor / reviewer).

The node references a persisted agent by ``data.agent_id``. The task is taken from
``config.task`` (template-interpolated) or, failing that, the upstream node output.
If no agent_id is set, an ephemeral agent is synthesised from the node type's role.
"""
from __future__ import annotations

from ...domain.agent import Agent
from ...domain.enums import AgentRole
from ...domain.execution import Execution
from ...domain.workflow import WorkflowNode
from ..context import ExecutionContext
from ..services import EngineServices
from .base import NodeResult, register_handler

_ROLE_FROM_TYPE = {
    "agent.supervisor": AgentRole.SUPERVISOR,
    "agent.planner": AgentRole.PLANNER,
    "agent.research": AgentRole.RESEARCHER,
    "agent.executor": AgentRole.EXECUTOR,
    "agent.reviewer": AgentRole.REVIEWER,
    "agent.openclaw": AgentRole.CUSTOM,
}


class AgentHandler:
    async def execute(self, node: WorkflowNode, ctx: ExecutionContext,
                      services: EngineServices, execution: Execution) -> NodeResult:
        config = ctx.interpolate(dict(node.data.config or {}))
        agent: Agent | None = None

        if node.data.agent_id:
            agent = await services.agent_repo.get(node.data.agent_id)
            if agent is None:
                return NodeResult.fail(f"Agent '{node.data.agent_id}' not found.")
        else:
            # Ephemeral agent derived from the node type + config.
            role = _ROLE_FROM_TYPE.get(node.type, AgentRole.CUSTOM)
            agent = Agent(
                name=node.data.label or node.type,
                role=role,
                tools=config.get("tools", []),
                model=config.get("model"),
                system_prompt=config.get("system_prompt"),
            )

        task = config.get("task") or config.get("prompt") or ""
        if not task:
            # Fall back to the most recent upstream output.
            task = str(ctx.snapshot().get("nodes", {}))
        await services.emit_event("node.agent_start",
                                  {"execution_id": execution.id, "node_id": node.id,
                                   "agent": agent.name})
        result = await services.agent_runtime.run(
            agent, task=str(task), context=ctx.snapshot(),
            run_key=f"{execution.id}:{node.id}")
        await services.write_audit(actor="agent", agent=agent.name, action="agent_run",
                                   result=result.get("status", "success"),
                                   execution_id=execution.id, detail={"node": node.id})
        if result.get("status") == "error":
            return NodeResult.fail(result.get("error", "agent error"))
        return NodeResult.ok({"output": result.get("output"), "steps": result.get("steps", [])})


_handler = AgentHandler()
for _t in ("agent", "agent.openclaw", "agent.supervisor", "agent.planner",
           "agent.research", "agent.executor", "agent.reviewer"):
    register_handler(_t, _handler)
