"""Global agent and tool registry.

Agents and tools register themselves by importing their modules.
The :py:func:`load_all` function triggers those imports so callers
don't need to know every module name.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from core.base_agent import BaseAgent
from core.base_tool import BaseTool


class _Registry:
    def __init__(self) -> None:
        self._agents: Dict[str, BaseAgent] = {}
        self._tools: Dict[str, BaseTool] = {}

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register_agent(self, agent: BaseAgent) -> None:
        self._agents[agent.agent_id] = agent

    def register_tool(self, tool: BaseTool) -> None:
        self._tools[tool.tool_id] = tool

    # ------------------------------------------------------------------
    # Look-up
    # ------------------------------------------------------------------

    def get_agent(self, agent_id: str) -> Optional[BaseAgent]:
        return self._agents.get(agent_id)

    def get_tool(self, tool_id: str) -> Optional[BaseTool]:
        return self._tools.get(tool_id)

    def list_agents(self) -> List[str]:
        return list(self._agents.keys())

    def list_tools(self) -> List[str]:
        return list(self._tools.keys())

    def is_loaded(self) -> bool:
        return bool(self._agents) and bool(self._tools)


# Singleton
Registry = _Registry()


def load_all() -> None:
    """Import agent and tool packages to trigger self-registration."""
    if Registry.is_loaded():
        return
    import agents  # noqa: F401  – side-effect: registers all agents
    import tools   # noqa: F401  – side-effect: registers all tools
