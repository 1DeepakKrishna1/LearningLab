"""agent-001 – Data Ingestion Agent."""

from typing import Any, Dict

from agents._base_impl import AgentMixin
from core.registry import Registry


class DataIngestionAgent(AgentMixin):
    @property
    def agent_id(self) -> str:
        return "agent-001"

    def name(self) -> str:
        return "Data Ingestion Agent"

    def description(self) -> str:
        return "Fetches data from external sources via APIs or file systems"

    def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        tool_results = self._run_tools(state)
        merged = self._merge_tool_results(tool_results)

        # Normalise: collect all records from HTTP or file tool outputs
        records = (
            merged.get("records")
            or merged.get("response_body", {}).get("data", [])
            or []
        )

        state["current_data"].update(
            {
                "records": records,
                "ingestion_source": merged.get("url") or merged.get("path", "unknown"),
                "records_fetched": len(records),
                "ingestion_metadata": {
                    "http_status": merged.get("http_status"),
                    "latency_ms": merged.get("latency_ms"),
                    "file_size_bytes": merged.get("metadata", {}).get("size_bytes"),
                },
            }
        )
        return state


Registry.register_agent(DataIngestionAgent())
