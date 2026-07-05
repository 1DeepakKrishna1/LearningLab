"""tool-011 – REST API Caller (dummy implementation)."""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict

from core.base_tool import BaseTool
from core.registry import Registry


class RestApiCallerTool(BaseTool):
    @property
    def tool_id(self) -> str:
        return "tool-011"

    def name(self) -> str:
        return "REST API Caller"

    def description(self) -> str:
        return "Authenticated REST API calls with OAuth2, API keys, retries and response parsing"

    def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        base_url = input_data.get("base_url", "https://api.example.com")
        auth_type = input_data.get("auth_type", "bearer")
        parse_response = input_data.get("parse_response", "json")

        return {
            "api_call_status": "success",
            "request_id": str(uuid.uuid4()),
            "base_url": base_url,
            "auth_type": auth_type,
            "http_status": 200,
            "parse_response": parse_response,
            "data": {
                "items": [
                    {"id": "a1b2", "label": "Result A", "score": 0.95},
                    {"id": "c3d4", "label": "Result B", "score": 0.87},
                ],
                "total": 2,
                "page": 1,
            },
            "latency_ms": 210,
            "called_at": datetime.now(timezone.utc).isoformat(),
        }


Registry.register_tool(RestApiCallerTool())
