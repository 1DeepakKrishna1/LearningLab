"""agent-003 – AI Analyst Agent."""

from typing import Any, Dict

from agents._base_impl import AgentMixin
from core.registry import Registry


class AIAnalystAgent(AgentMixin):
    @property
    def agent_id(self) -> str:
        return "agent-003"

    def name(self) -> str:
        return "AI Analyst"

    def description(self) -> str:
        return "Applies AI/ML models to derive insights and classify data"

    def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        tool_results = self._run_tools(state)
        merged = self._merge_tool_results(tool_results)

        state["current_data"].update(
            {
                "ai_analysis": merged.get("response", ""),
                "confidence": merged.get("confidence", 0.0),
                "classifications": merged.get("classifications", []),
                "inference_id": merged.get("inference_id", ""),
                "model_used": merged.get("model", ""),
                "tokens_used": merged.get("total_tokens", 0),
                "analysis_metadata": {
                    "prompt_tokens": merged.get("prompt_tokens"),
                    "completion_tokens": merged.get("completion_tokens"),
                    "finish_reason": merged.get("finish_reason"),
                },
            }
        )
        return state


Registry.register_agent(AIAnalystAgent())
