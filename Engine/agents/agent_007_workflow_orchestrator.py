"""agent-007 – Workflow Orchestrator Agent."""

from typing import Any, Dict

from agents._base_impl import AgentMixin
from core.registry import Registry


class WorkflowOrchestratorAgent(AgentMixin):
    @property
    def agent_id(self) -> str:
        return "agent-007"

    def name(self) -> str:
        return "Workflow Orchestrator"

    def description(self) -> str:
        return "Routes execution based on conditions and triggers downstream webhooks"

    def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        cfg = state.get("current_node_config", {}).get("properties", {})
        field = cfg.get("condition_field", "status")
        operator = cfg.get("condition_operator", "equals")
        expected = cfg.get("condition_value", "active")
        actual = state.get("current_data", {}).get(field, "")

        condition_met = (
            (operator == "equals" and str(actual) == str(expected))
            or (operator == "not_equals" and str(actual) != str(expected))
            or (operator == "contains" and str(expected) in str(actual))
        )

        tool_results = self._run_tools(state)
        merged = self._merge_tool_results(tool_results)

        state["current_data"].update(
            {
                "condition_field": field,
                "condition_met": condition_met,
                "route": "primary" if condition_met else "secondary",
                "webhook_delivery_id": merged.get("delivery_id", ""),
                "orchestrator_decision": "route_primary" if condition_met else "route_secondary",
            }
        )
        return state


Registry.register_agent(WorkflowOrchestratorAgent())
