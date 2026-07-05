"""tool-001 – HTTP Request (dummy implementation)."""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict

from core.base_tool import BaseTool
from core.registry import Registry


class HttpRequestTool(BaseTool):
    @property
    def tool_id(self) -> str:
        return "tool-001"

    def name(self) -> str:
        return "HTTP Request"

    def description(self) -> str:
        return "Make HTTP GET/POST/PUT/DELETE requests to external APIs"

    def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        method = input_data.get("method", "GET").upper()
        url = input_data.get("url", "https://api.example.com/data")
        return {
            "http_status": 200,
            "method": method,
            "url": url,
            "response_body": {
                "status": "success",
                "request_id": str(uuid.uuid4()),
                "data": [
                    {"id": i, "value": f"item_{i}", "active": True}
                    for i in range(1, 4)
                ],
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
            "response_headers": {
                "content-type": "application/json",
                "x-request-id": str(uuid.uuid4()),
            },
            "latency_ms": 142,
        }


Registry.register_tool(HttpRequestTool())
