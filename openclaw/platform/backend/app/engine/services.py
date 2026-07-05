"""Collaborators the engine and node handlers depend on (injected, not imported)."""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Awaitable, Callable, Optional

if TYPE_CHECKING:
    from ..agents.runtime import AgentRuntimeManager
    from ..domain.agent import Agent
    from ..domain.approval import Approval
    from ..registry.tool_registry import ToolRegistry
    from ..storage.repository import Repository

# (event_type, payload) -> None
EmitFn = Callable[[str, dict[str, Any]], Awaitable[None]]
# (action, result, detail) -> None
AuditFn = Callable[..., Awaitable[None]]


@dataclass
class EngineServices:
    """Everything node handlers need, supplied by the DI container."""

    registry: "ToolRegistry"
    agent_runtime: "AgentRuntimeManager"
    agent_repo: "Repository[Agent]"
    approval_repo: "Repository[Approval]"
    messaging: Any = None                     # MessagingProvider | None
    emit: Optional[EmitFn] = None
    audit: Optional[AuditFn] = None
    default_model: str = "claude-sonnet-4-6"

    async def emit_event(self, event_type: str, payload: dict[str, Any]) -> None:
        if self.emit:
            await self.emit(event_type, payload)

    async def write_audit(self, **kwargs: Any) -> None:
        if self.audit:
            await self.audit(**kwargs)
