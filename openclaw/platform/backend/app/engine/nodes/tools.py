"""Generic tool node handler.

A node of type ``tool.<category>.<name>`` is executed by resolving the registry
manifest and running it with the node's (interpolated) config as inputs. New tools
require no new handler — this one serves them all.
"""
from __future__ import annotations

from ...domain.execution import Execution
from ...domain.workflow import WorkflowNode
from ..context import ExecutionContext
from ..services import EngineServices
from .base import NodeResult, register_handler


class ToolHandler:
    async def execute(self, node: WorkflowNode, ctx: ExecutionContext,
                      services: EngineServices, execution: Execution) -> NodeResult:
        tool_id = node.data.tool_id or node.type[len("tool."):]
        tool_id = services.registry.normalise_id(tool_id)
        if services.registry.try_get(tool_id) is None:
            return NodeResult.fail(f"Unknown tool '{tool_id}'.")

        inputs = ctx.interpolate(dict(node.data.config or {}))
        await services.emit_event("node.tool_call",
                                  {"execution_id": execution.id, "node_id": node.id,
                                   "tool": tool_id, "inputs": inputs})
        result = await services.registry.execute(tool_id, inputs)
        await services.write_audit(actor="agent", action="tool_call",
                                   result=result.get("status", "success"),
                                   execution_id=execution.id,
                                   detail={"tool": tool_id, "node": node.id})
        if result.get("status") == "error":
            return NodeResult.fail(result.get("message", "tool error"))
        return NodeResult.ok(result)


register_handler("tool", ToolHandler())
