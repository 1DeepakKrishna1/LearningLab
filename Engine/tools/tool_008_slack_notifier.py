"""tool-008 – Slack Notifier (dummy implementation)."""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict

from core.base_tool import BaseTool
from core.registry import Registry


class SlackNotifierTool(BaseTool):
    @property
    def tool_id(self) -> str:
        return "tool-008"

    def name(self) -> str:
        return "Slack Notifier"

    def description(self) -> str:
        return "Send messages to Slack channels or direct messages"

    def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        channel = input_data.get("channel", "#general")
        workflow_name = input_data.get("workflow_name", "Workflow")
        status = input_data.get("status", "completed")

        message = (
            f"*[{workflow_name}]* Execution {status} ✅\n"
            f">Timestamp: {datetime.now(timezone.utc).isoformat()}"
        )

        return {
            "slack_sent": True,
            "message_ts": str(uuid.uuid4()),
            "channel": channel,
            "message": message,
            "permalink": f"https://slack.example.com/archives/{channel}/{uuid.uuid4()}",
        }


Registry.register_tool(SlackNotifierTool())
