"""agent-end – Workflow End agent."""

from typing import Any, Dict

from agents._base_impl import AgentMixin
from core.registry import Registry


class WorkflowEndAgent(AgentMixin):
    @property
    def agent_id(self) -> str:
        return "agent-end"

    def name(self) -> str:
        return "Workflow End"

    def description(self) -> str:
        return "Exit point of the workflow. Collects final results into end_properties."

    def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        props = state.get("current_node_config", {}).get("properties", {})
        # Capture the full flowing data as the workflow's final output
        state["end_properties"] = {**state.get("current_data", {}), **props}
        state["current_data"]["_workflow_ended"] = True
        return state


Registry.register_agent(WorkflowEndAgent())
