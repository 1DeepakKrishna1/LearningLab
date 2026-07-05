"""Shared implementation helpers for all agents."""

from __future__ import annotations

from typing import Any, Dict, List

from core import state as state_utils
from core.base_agent import BaseAgent
from core.registry import Registry


class AgentMixin(BaseAgent):
    """Mixin that provides common tool-execution plumbing for concrete agents."""

    def _run_tools(self, state: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Execute every tool listed in the current node config and return results."""
        node_id = state.get("current_node_id", "")
        node_cfg = state.get("current_node_config", {})
        tool_ids: List[str] = node_cfg.get("tools", [])
        tool_cfgs: Dict[str, Any] = node_cfg.get("toolConfigs", {})

        results: List[Dict[str, Any]] = []
        for tool_id in tool_ids:
            tool = Registry.get_tool(tool_id)
            if tool is None:
                state_utils.log_event(
                    state, "WARNING", node_id, "", "tool_skipped",
                    {"tool_id": tool_id, "reason": "not registered"},
                )
                continue

            tool_input = {**state.get("current_data", {}), **tool_cfgs.get(tool_id, {})}
            tool_output = tool.run(tool_input)

            state_utils.add_tool_execution(
                state, node_id, tool_id, tool.name(), tool_input, tool_output
            )
            state_utils.log_event(
                state, "INFO", node_id, "", "tool_completed",
                {"tool_id": tool_id, "tool_name": tool.name()},
            )
            results.append({"tool_id": tool_id, "tool_name": tool.name(), "output": tool_output})

        return results

    def _merge_tool_results(
        self, results: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Merge all tool outputs into a single flat dict."""
        merged: Dict[str, Any] = {}
        for r in results:
            merged.update(r.get("output", {}))
        return merged
