"""agent-009 – Role-Based Approver Agent."""

from typing import Any, Dict

from agents._base_impl import AgentMixin
from core.registry import Registry


class RoleBasedApproverAgent(AgentMixin):
    @property
    def agent_id(self) -> str:
        return "agent-009"

    def name(self) -> str:
        return "Role-Based Approver"

    def description(self) -> str:
        return "Routes tasks to role-specific approvers based on business rules"

    def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        cfg = state.get("current_node_config", {}).get("properties", {})
        roles = cfg.get("roles", ["manager"])
        require_all = cfg.get("require_all", False)

        tool_results = self._run_tools(state)
        merged = self._merge_tool_results(tool_results)

        # Simulate each role approving
        approvals = [
            {"role": role, "decision": "approved", "approver": f"{role}@example.com"}
            for role in roles
        ]
        all_approved = all(a["decision"] == "approved" for a in approvals)
        any_approved = any(a["decision"] == "approved" for a in approvals)
        final_decision = "approved" if (
            (require_all and all_approved) or (not require_all and any_approved)
        ) else "rejected"

        state["current_data"].update(
            {
                "role_approvals": approvals,
                "require_all": require_all,
                "role_based_decision": final_decision,
                "approval_id": merged.get("approval_id", ""),
                "notification_sent": bool(merged.get("email_sent")),
            }
        )
        return state


Registry.register_agent(RoleBasedApproverAgent())
