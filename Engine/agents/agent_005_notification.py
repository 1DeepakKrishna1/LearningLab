"""agent-005 – Notification Agent."""

from typing import Any, Dict

from agents._base_impl import AgentMixin
from core.registry import Registry


class NotificationAgent(AgentMixin):
    @property
    def agent_id(self) -> str:
        return "agent-005"

    def name(self) -> str:
        return "Notification Agent"

    def description(self) -> str:
        return "Sends status updates and alerts via email and Slack"

    def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        # Inject workflow context so notifier tools can render templates
        state["current_data"].setdefault("workflow_name", state.get("workflow_name", "Workflow"))
        state["current_data"].setdefault("status", "completed")

        tool_results = self._run_tools(state)
        merged = self._merge_tool_results(tool_results)

        state["current_data"].update(
            {
                "notifications_sent": True,
                "email_message_id": merged.get("message_id", ""),
                "slack_message_ts": merged.get("message_ts", ""),
                "notification_channels": [
                    ch for ch in ["email", "slack"]
                    if merged.get("email_sent") or merged.get("slack_sent")
                ],
            }
        )
        return state


Registry.register_agent(NotificationAgent())
