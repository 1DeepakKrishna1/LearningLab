"""Agent Runtime Manager — builds and runs OpenClaw agents from definitions.

Bridges persisted :class:`Agent` records (agents.json) and the live
:class:`OpenClawAgent` runtime, enforcing per-agent security limits and the tool
allow-list against the registry.
"""
from __future__ import annotations

from typing import Any

from ..config import Settings
from ..domain.agent import Agent
from ..logging_setup import get_logger
from ..registry.tool_registry import ToolRegistry
from .openclaw_agent import OpenClawAgent

logger = get_logger("agent.runtime")


class AgentRuntimeManager:
    """Factory + executor for agents. Tracks active runs for monitoring."""

    def __init__(self, settings: Settings, registry: ToolRegistry) -> None:
        self._settings = settings
        self._registry = registry
        self._active: dict[str, str] = {}  # run_key -> agent name (for dashboard)

    def build(self, agent: Agent) -> OpenClawAgent:
        """Construct a runnable agent, validating its tool allow-list."""
        unknown = [
            t for t in (agent.limits.tool_allow_list or agent.tools)
            if self._registry.try_get(self._registry.normalise_id(t)) is None
        ]
        if unknown:
            logger.warning("Agent '%s' references unknown tools: %s", agent.name, unknown)
        return OpenClawAgent(
            agent=agent,
            registry=self._registry,
            default_provider=self._settings.default_llm_provider,
            default_model=self._settings.default_llm_model,
        )

    async def run(self, agent: Agent, task: str,
                  context: dict[str, Any] | None = None,
                  run_key: str | None = None) -> dict[str, Any]:
        """Build and execute an agent against a task."""
        runnable = self.build(agent)
        key = run_key or agent.agent_id
        self._active[key] = agent.name
        logger.info("Agent run start: %s (role=%s, tools=%d)",
                    agent.name, agent.role, len(agent.tools))
        try:
            result = await runnable.run(task, context)
        finally:
            self._active.pop(key, None)
        logger.info("Agent run end: %s -> %s", agent.name, result.get("status"))
        return result

    @property
    def active_count(self) -> int:
        return len(self._active)

    def active_agents(self) -> list[str]:
        return list(self._active.values())
