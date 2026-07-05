"""agent-015 – Supervisor Agent."""

from datetime import datetime, timezone
from typing import Any, Dict

from agents._base_impl import AgentMixin
from core.registry import Registry


class SupervisorAgent(AgentMixin):
    @property
    def agent_id(self) -> str:
        return "agent-015"

    def name(self) -> str:
        return "Supervisor"

    def description(self) -> str:
        return "Monitors agent health, routes tasks by policy, catches failures and triggers retries or escalations"

    def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        cfg = state.get("current_node_config", {}).get("properties", {})
        routing_policy = cfg.get("routing_policy", "round_robin")
        max_retries = int(cfg.get("max_retries", 3))
        failure_threshold = int(cfg.get("failure_threshold", 2))
        escalation_channel = cfg.get("escalation_channel", "#ops-alerts")

        tool_results = self._run_tools(state)
        merged = self._merge_tool_results(tool_results)

        # Simulate health check
        node_records = state.get("node_records", {})
        failed_nodes = [
            nid for nid, rec in node_records.items()
            if rec.get("status") == "failed"
        ]
        health_status = "degraded" if failed_nodes else "healthy"
        escalated = len(failed_nodes) >= failure_threshold

        state["current_data"].update(
            {
                "supervisor_health_status": health_status,
                "supervisor_routing_policy": routing_policy,
                "failed_nodes": failed_nodes,
                "escalated": escalated,
                "escalation_channel": escalation_channel if escalated else None,
                "max_retries": max_retries,
                "heartbeat": datetime.now(timezone.utc).isoformat(),
                "slack_message_ts": merged.get("message_ts", ""),
                "email_message_id": merged.get("message_id", ""),
            }
        )
        return state


Registry.register_agent(SupervisorAgent())
