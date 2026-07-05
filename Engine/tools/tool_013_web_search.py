"""tool-013 – Web Search (dummy implementation)."""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict

from core.base_tool import BaseTool
from core.registry import Registry


class WebSearchTool(BaseTool):
    @property
    def tool_id(self) -> str:
        return "tool-013"

    def name(self) -> str:
        return "Web Search"

    def description(self) -> str:
        return "Real-time web search to retrieve up-to-date information from the internet"

    def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        query = input_data.get("user_query", input_data.get("query", "latest AI trends"))
        max_results = int(input_data.get("max_results", 5))
        engine = input_data.get("engine", "tavily")

        results = [
            {
                "rank": i + 1,
                "title": f"Dummy Search Result {i + 1} for '{query}'",
                "url": f"https://example.com/result-{uuid.uuid4().hex[:8]}",
                "snippet": (
                    f"This is a simulated search result snippet for query '{query}'. "
                    f"It contains relevant information matching the search intent. "
                    f"Published {datetime.now(timezone.utc).strftime('%Y-%m-%d')}."
                ),
                "score": round(0.95 - i * 0.08, 2),
            }
            for i in range(min(max_results, 5))
        ]

        return {
            "search_engine": engine,
            "query": query,
            "total_results": len(results),
            "results": results,
            "search_depth": input_data.get("search_depth", "advanced"),
            "searched_at": datetime.now(timezone.utc).isoformat(),
        }


Registry.register_tool(WebSearchTool())
