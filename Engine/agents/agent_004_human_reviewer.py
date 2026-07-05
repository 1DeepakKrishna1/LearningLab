"""agent-004 – Human Reviewer Agent."""

from typing import Any, Dict

from agents._base_impl import AgentMixin
from core.registry import Registry


class HumanReviewerAgent(AgentMixin):
    @property
    def agent_id(self) -> str:
        return "agent-004"

    def name(self) -> str:
        return "Human Reviewer"

    def description(self) -> str:
        return "Routes items to human reviewers and waits for approval decisions"

    def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        tool_results = self._run_tools(state)
        merged = self._merge_tool_results(tool_results)

        state["current_data"].update(
            {
                "review_decision": merged.get("decision", "approved"),
                "reviewed_by": merged.get("decided_by", "human-reviewer"),
                "review_comments": merged.get("comments", ""),
                "approval_id": merged.get("approval_id", ""),
                "review_completed_at": merged.get("decided_at", ""),
                "human_review_required": True,
            }
        )
        return state


Registry.register_agent(HumanReviewerAgent())
