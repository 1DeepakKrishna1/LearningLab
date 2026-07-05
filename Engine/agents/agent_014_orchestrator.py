"""agent-014 – Orchestrator Agent."""

from typing import Any, Dict, List

from agents._base_impl import AgentMixin
from core.registry import Registry


class OrchestratorAgent(AgentMixin):
    @property
    def agent_id(self) -> str:
        return "agent-014"

    def name(self) -> str:
        return "Orchestrator"

    def description(self) -> str:
        return "Decomposes complex tasks, dispatches sub-tasks to specialist agents and merges results"

    def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        cfg = state.get("current_node_config", {}).get("properties", {})
        decomposition_strategy = cfg.get("decomposition_strategy", "llm")
        merge_strategy = cfg.get("merge_strategy", "reduce")
        max_sub_agents = int(cfg.get("max_sub_agents", 5))

        tool_results = self._run_tools(state)
        merged = self._merge_tool_results(tool_results)

        # Simulate task decomposition
        sub_tasks: List[Dict[str, Any]] = [
            {
                "sub_task_id": f"sub_{i+1}",
                "description": f"Sub-task {i+1}: process data partition {i+1}",
                "assigned_to": f"specialist_agent_{i+1}",
                "status": "completed",
                "result": f"Sub-task {i+1} completed successfully.",
            }
            for i in range(min(2, max_sub_agents))
        ]

        # Simulate merge
        merged_result = " | ".join(st["result"] for st in sub_tasks)

        state["current_data"].update(
            {
                "decomposition_strategy": decomposition_strategy,
                "sub_tasks": sub_tasks,
                "sub_tasks_count": len(sub_tasks),
                "merge_strategy": merge_strategy,
                "orchestrator_merged_result": merged_result,
                "webhook_delivery_id": merged.get("delivery_id", ""),
            }
        )
        return state


Registry.register_agent(OrchestratorAgent())
