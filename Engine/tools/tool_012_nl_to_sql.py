"""tool-012 – NL-to-SQL (dummy implementation)."""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict

from core.base_tool import BaseTool
from core.registry import Registry


class NLToSQLTool(BaseTool):
    @property
    def tool_id(self) -> str:
        return "tool-012"

    def name(self) -> str:
        return "NL-to-SQL"

    def description(self) -> str:
        return "Convert natural language questions into SQL queries and execute against a database"

    def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        nl_query = input_data.get("user_query", "Show me recent orders")
        max_rows = int(input_data.get("max_rows", 10))

        generated_sql = (
            f"SELECT o.id, c.name, o.amount, o.status, o.created_at "
            f"FROM orders o "
            f"JOIN customers c ON o.customer_id = c.id "
            f"WHERE o.status = 'pending' "
            f"ORDER BY o.created_at DESC "
            f"LIMIT {max_rows};"
        )

        dummy_rows = [
            {
                "id": str(uuid.uuid4())[:8],
                "name": f"Customer {chr(65+i)}",
                "amount": round(100.0 * (i + 1), 2),
                "status": "pending",
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
            for i in range(3)
        ]

        return {
            "nl_query": nl_query,
            "generated_sql": generated_sql,
            "rows_returned": len(dummy_rows),
            "results": dummy_rows,
            "execution_time_ms": 55,
            "confidence": 0.93,
        }


Registry.register_tool(NLToSQLTool())
