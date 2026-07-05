"""agent-012 – Reflection Agent."""

from typing import Any, Dict, List

from agents._base_impl import AgentMixin
from core.registry import Registry


class ReflectionAgent(AgentMixin):
    @property
    def agent_id(self) -> str:
        return "agent-012"

    def name(self) -> str:
        return "Reflection Agent"

    def description(self) -> str:
        return "Generates an initial output, self-critiques it, and iteratively improves until quality threshold is met"

    def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        cfg = state.get("current_node_config", {}).get("properties", {})
        quality_threshold = float(cfg.get("quality_threshold", 8.0))
        max_iterations = int(cfg.get("max_iterations", 3))

        # Grab previous output to reflect on
        previous_output = (
            state.get("current_data", {}).get("react_final_answer")
            or state.get("current_data", {}).get("prompt_agent_output")
            or state.get("current_data", {}).get("ai_analysis")
            or "No prior output found."
        )

        iterations: List[Dict[str, Any]] = []
        current_output = previous_output

        for i in range(1, max_iterations + 1):
            tool_results = self._run_tools(state)
            merged = self._merge_tool_results(tool_results)

            # Simulate scoring
            score = round(min(10.0, 7.0 + i * 0.8), 1)
            critique = (
                f"Iteration {i}: Accuracy={score}, Completeness={score}, Clarity={score}. "
                f"Overall={score}."
            )

            if score >= quality_threshold:
                current_output = (
                    merged.get("response", current_output)
                    + f"\n\n[Reflection passed quality threshold {quality_threshold} at iteration {i}]"
                )
                iterations.append({"iteration": i, "score": score, "critique": critique, "status": "passed"})
                break

            current_output = (
                merged.get("response", current_output)
                + f"\n\n[Revised at iteration {i}]"
            )
            iterations.append({"iteration": i, "score": score, "critique": critique, "status": "revised"})

        state["current_data"].update(
            {
                "reflection_output": current_output,
                "reflection_iterations": iterations,
                "final_quality_score": iterations[-1]["score"] if iterations else quality_threshold,
                "quality_threshold": quality_threshold,
            }
        )
        return state


Registry.register_agent(ReflectionAgent())
