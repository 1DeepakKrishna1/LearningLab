"""tool-007 – Approval Gate (dummy implementation)."""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict

from core.base_tool import BaseTool
from core.registry import Registry


class ApprovalGateTool(BaseTool):
    @property
    def tool_id(self) -> str:
        return "tool-007"

    def name(self) -> str:
        return "Approval Gate"

    def description(self) -> str:
        return "Pause workflow and wait for human approval before proceeding"

    def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        approvers = input_data.get("approvers", ["reviewer@example.com"])
        timeout_hours = int(input_data.get("timeout_hours", 24))
        auto_approve = input_data.get("auto_approve_on_timeout", False)

        # Dummy: auto-approve immediately
        return {
            "approval_id": str(uuid.uuid4()),
            "decision": "approved",
            "decided_by": approvers[0] if approvers else "auto",
            "decided_at": datetime.now(timezone.utc).isoformat(),
            "timeout_hours": timeout_hours,
            "auto_approved": auto_approve,
            "comments": "Approved during automated dummy execution.",
        }


Registry.register_tool(ApprovalGateTool())
