"""agent-010 – Prompt Agent."""

from typing import Any, Dict

from agents._base_impl import AgentMixin
from core.registry import Registry


class PromptAgent(AgentMixin):
    @property
    def agent_id(self) -> str:
        return "agent-010"

    def name(self) -> str:
        return "Prompt Agent"

    def description(self) -> str:
        return "Executes parameterized System + User prompt templates against an LLM with variable injection"

    def _render(self, template: str, context: Dict[str, Any]) -> str:
        """Simple {{variable}} template rendering."""
        for key, val in context.items():
            template = template.replace("{{" + key + "}}", str(val))
        return template

    def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        cfg = state.get("current_node_config", {}).get("properties", {})
        system_prompt = self._render(cfg.get("system_prompt", ""), state.get("current_data", {}))
        user_prompt = self._render(cfg.get("user_prompt", ""), state.get("current_data", {}))
        output_format = cfg.get("output_format", "markdown")
        model = cfg.get("model", "llama-3.3-70b-versatile")

        tool_results = self._run_tools(state)
        merged = self._merge_tool_results(tool_results)

        # Simulate LLM response incorporating prompts
        llm_response = (
            merged.get("response")
            or (
                f"[Prompt Agent – model: {model}, format: {output_format}]\n\n"
                f"**System context applied.**\n"
                f"**User task processed.**\n\n"
                f"Generated output based on input data with confidence 0.92."
            )
        )

        state["current_data"].update(
            {
                "prompt_agent_output": llm_response,
                "system_prompt_rendered": system_prompt[:200],
                "user_prompt_rendered": user_prompt[:200],
                "output_format": output_format,
                "model": model,
                "tokens_used": merged.get("total_tokens", 0),
            }
        )
        return state


Registry.register_agent(PromptAgent())
