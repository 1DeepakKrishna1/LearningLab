"""Node handler contract and the handler registry.

A handler turns a node + context into a :class:`NodeResult`. The result's
``control`` field carries a branch key (matched against edge ``sourceHandle``) so
logic nodes can steer the DAG. ``suspend`` signals the executor to pause the whole
run (approval / wait nodes).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Awaitable, Callable, Protocol

from ...domain.workflow import WorkflowNode

if TYPE_CHECKING:
    from ..context import ExecutionContext
    from ..services import EngineServices
    from ...domain.execution import Execution


@dataclass
class NodeResult:
    status: str = "completed"          # completed | failed | skipped | waiting
    output: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    control: str | None = None         # branch key for conditional edges
    suspend: dict[str, Any] | None = None  # set when the run must pause here

    @classmethod
    def ok(cls, output: dict[str, Any] | None = None, control: str | None = None) -> "NodeResult":
        return cls(status="completed", output=output or {}, control=control)

    @classmethod
    def fail(cls, error: str) -> "NodeResult":
        return cls(status="failed", error=error)

    @classmethod
    def waiting(cls, suspend: dict[str, Any]) -> "NodeResult":
        return cls(status="waiting", suspend=suspend)


class NodeHandler(Protocol):
    async def execute(self, node: WorkflowNode, ctx: "ExecutionContext",
                      services: "EngineServices", execution: "Execution") -> NodeResult: ...


# --- handler registry, keyed by node-type prefix ---
_HANDLERS: dict[str, NodeHandler] = {}


def register_handler(prefix: str, handler: NodeHandler) -> None:
    _HANDLERS[prefix] = handler


def resolve_handler(node_type: str) -> NodeHandler | None:
    """Resolve the handler for a node type, matching the most specific prefix."""
    group = node_type.split(".", 1)[0]
    # tool.* always routes to the generic tool handler.
    if group == "tool":
        return _HANDLERS.get("tool")
    # Exact type match first (e.g. logic.approval), then group fallback.
    return _HANDLERS.get(node_type) or _HANDLERS.get(group)


EmitFn = Callable[[str, dict[str, Any]], Awaitable[None]]
