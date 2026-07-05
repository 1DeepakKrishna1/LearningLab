"""agent-start – Workflow Start agent."""

from typing import Any, Dict

from agents._base_impl import AgentMixin
from core.registry import Registry


class WorkflowStartAgent(AgentMixin):
    @property
    def agent_id(self) -> str:
        return "agent-start"

    def name(self) -> str:
        return "Workflow Start"

    def description(self) -> str:
        return "Entry point of the workflow. Injects start_properties into current_data."

    def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        props = state.get("current_node_config", {}).get("properties", {})
        state["current_data"].update(props)
        state["current_data"]["_workflow_started"] = True
        return state


Registry.register_agent(WorkflowStartAgent())
