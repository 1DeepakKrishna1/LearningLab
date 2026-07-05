"""tool-004 – Database Query (dummy implementation)."""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict

from core.base_tool import BaseTool
from core.registry import Registry


class DatabaseQueryTool(BaseTool):
    @property
    def tool_id(self) -> str:
        return "tool-004"

    def name(self) -> str:
        return "Database Query"

    def description(self) -> str:
        return "Execute SQL queries against connected databases"

    def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        table = input_data.get("table_name", "records")
        limit = int(input_data.get("max_rows", 5))
        operation = input_data.get("operation", "SELECT")

        dummy_rows = [
            {
                "id": str(uuid.uuid4())[:8],
                "table": table,
                "value": f"row_{i}",
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
            for i in range(1, min(limit, 5) + 1)
        ]

        return {
            "query_status": "success",
            "operation": operation,
            "rows_affected": len(dummy_rows),
            "rows": dummy_rows,
            "execution_time_ms": 38,
            "connection": "postgresql://dummy:5432/db",
        }


Registry.register_tool(DatabaseQueryTool())
