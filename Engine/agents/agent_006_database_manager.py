"""agent-006 – Database Manager Agent."""

from typing import Any, Dict

from agents._base_impl import AgentMixin
from core.registry import Registry


class DatabaseManagerAgent(AgentMixin):
    @property
    def agent_id(self) -> str:
        return "agent-006"

    def name(self) -> str:
        return "Database Manager"

    def description(self) -> str:
        return "Persists processed records to the configured database"

    def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        tool_results = self._run_tools(state)
        merged = self._merge_tool_results(tool_results)

        state["current_data"].update(
            {
                "db_operation_status": merged.get("query_status", "success"),
                "rows_persisted": merged.get("rows_affected", 0),
                "db_rows": merged.get("rows", []),
                "db_execution_time_ms": merged.get("execution_time_ms", 0),
                "nl_to_sql_query": merged.get("generated_sql", ""),
                "nl_query_results": merged.get("results", []),
            }
        )
        return state


Registry.register_agent(DatabaseManagerAgent())
