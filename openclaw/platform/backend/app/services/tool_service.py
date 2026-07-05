"""Tool service — exposes the registry and the node-palette catalog to the API."""
from __future__ import annotations

from typing import Any

from ..domain.tool import ToolManifest
from ..registry.tool_registry import ToolRegistry

# Static (non-tool) node definitions for the workflow-builder palette.
STATIC_NODES: dict[str, list[dict[str, Any]]] = {
    "trigger": [
        {"type": "trigger.manual", "label": "Manual Trigger", "icon": "play"},
        {"type": "trigger.http", "label": "HTTP Trigger", "icon": "globe"},
        {"type": "trigger.cron", "label": "Cron Trigger", "icon": "clock"},
        {"type": "trigger.webhook", "label": "Webhook Trigger", "icon": "webhook"},
        {"type": "trigger.email", "label": "Email Trigger", "icon": "mail"},
        {"type": "trigger.whatsapp", "label": "WhatsApp Trigger", "icon": "message-circle"},
        {"type": "trigger.file_upload", "label": "File Upload Trigger", "icon": "upload"},
        {"type": "trigger.google_sheet_row", "label": "Google Sheet Row", "icon": "table"},
    ],
    "agent": [
        {"type": "agent.openclaw", "label": "OpenClaw Agent", "icon": "bot"},
        {"type": "agent.supervisor", "label": "Supervisor Agent", "icon": "users"},
        {"type": "agent.planner", "label": "Planner Agent", "icon": "list-checks"},
        {"type": "agent.research", "label": "Research Agent", "icon": "search"},
        {"type": "agent.executor", "label": "Executor Agent", "icon": "zap"},
        {"type": "agent.reviewer", "label": "Reviewer Agent", "icon": "shield-check"},
    ],
    "logic": [
        {"type": "logic.if_else", "label": "If / Else", "icon": "git-branch"},
        {"type": "logic.switch", "label": "Switch", "icon": "git-fork"},
        {"type": "logic.parallel", "label": "Parallel", "icon": "split"},
        {"type": "logic.merge", "label": "Merge", "icon": "merge"},
        {"type": "logic.loop", "label": "Loop", "icon": "repeat"},
        {"type": "logic.wait", "label": "Wait", "icon": "hourglass"},
        {"type": "logic.approval", "label": "Approval", "icon": "user-check"},
    ],
    "action": [
        {"type": "action.send_email", "label": "Send Email", "icon": "send"},
        {"type": "action.send_whatsapp", "label": "Send WhatsApp", "icon": "message-circle"},
        {"type": "action.api_call", "label": "API Call", "icon": "plug"},
        {"type": "action.file_write", "label": "File Write", "icon": "file-plus"},
        {"type": "action.generate_report", "label": "Generate Report", "icon": "file-text"},
    ],
}


class ToolService:
    def __init__(self, registry: ToolRegistry) -> None:
        self._registry = registry

    def list(self, query: str | None = None) -> list[ToolManifest]:
        return self._registry.search(query) if query else self._registry.all()

    def get(self, tool_id: str) -> ToolManifest | None:
        return self._registry.try_get(self._registry.normalise_id(tool_id))

    def categories(self) -> dict[str, list[ToolManifest]]:
        return self._registry.by_category()

    async def execute(self, tool_id: str, inputs: dict[str, Any]) -> dict[str, Any]:
        return await self._registry.execute(self._registry.normalise_id(tool_id), inputs)

    async def refresh(self) -> dict[str, int]:
        return await self._registry.refresh()

    def node_catalog(self) -> dict[str, Any]:
        """Full palette: static node groups + tool nodes grouped by category."""
        tool_nodes = {
            cat: [
                {"type": m.node_type, "label": m.display_name, "icon": m.icon,
                 "color": m.color, "tool_id": m.id, "description": m.description}
                for m in mans
            ]
            for cat, mans in self._registry.by_category().items()
        }
        return {"static": STATIC_NODES, "tools": tool_nodes}
