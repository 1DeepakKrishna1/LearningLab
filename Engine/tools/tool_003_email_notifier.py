"""tool-003 – Email Notifier (dummy implementation)."""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict

from core.base_tool import BaseTool
from core.registry import Registry


class EmailNotifierTool(BaseTool):
    @property
    def tool_id(self) -> str:
        return "tool-003"

    def name(self) -> str:
        return "Email Notifier"

    def description(self) -> str:
        return "Send email notifications to specified recipients"

    def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        recipients = input_data.get("recipients", ["stakeholder@example.com"])
        subject = input_data.get("subject", f"[{input_data.get('workflow_name', 'Workflow')}] Notification")
        workflow_name = input_data.get("workflow_name", "Workflow")
        status = input_data.get("status", "completed")

        return {
            "email_sent": True,
            "message_id": str(uuid.uuid4()),
            "recipients": recipients if isinstance(recipients, list) else [recipients],
            "subject": subject,
            "body_preview": (
                f"Workflow '{workflow_name}' status: {status}. "
                f"Sent at {datetime.now(timezone.utc).isoformat()}"
            ),
            "smtp_response": "250 OK",
        }


Registry.register_tool(EmailNotifierTool())
