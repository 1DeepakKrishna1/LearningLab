"""agent-011 – ReAct Agent."""

from typing import Any, Dict, List

from agents._base_impl import AgentMixin
from core.registry import Registry


class ReActAgent(AgentMixin):
    @property
    def agent_id(self) -> str:
        return "agent-011"

    def name(self) -> str:
        return "ReAct Agent"

    def description(self) -> str:
        return "Iteratively Reasons and Acts using tools until a final answer is reached"

    def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        cfg = state.get("current_node_config", {}).get("properties", {})
        max_iterations = int(cfg.get("max_iterations", 6))
        trace_thoughts = cfg.get("trace_thoughts", True)
        goal = cfg.get("goal_prompt", "Achieve goal")

        thought_trace: List[Dict[str, Any]] = []
        final_answer = ""

        # Simulate the ReAct loop: run tools once per simulated iteration
        for iteration in range(1, min(3, max_iterations) + 1):
            tool_results = self._run_tools(state)
            merged = self._merge_tool_results(tool_results)

            thought = (
                f"[Iteration {iteration}] Reasoning: Analysed available data. "
                f"Action: invoked tools. Observation: received {len(tool_results)} tool result(s)."
            )
            thought_trace.append(
                {
                    "iteration": iteration,
                    "thought": thought,
                    "tools_called": [r["tool_id"] for r in tool_results],
                    "observation": str(merged)[:200],
                }
            )

            # Check if we have enough to form a final answer
            if merged.get("results") or merged.get("response") or merged.get("data"):
                final_answer = (
                    merged.get("response")
                    or f"Final answer derived after {iteration} iteration(s). "
                       f"Search results: {len(merged.get('results', []))} items found."
                )
                break

        if not final_answer:
            final_answer = f"ReAct agent completed {max_iterations} iterations. No definitive answer reached."

        state["current_data"].update(
            {
                "react_final_answer": final_answer,
                "react_iterations": len(thought_trace),
                "react_thought_trace": thought_trace if trace_thoughts else [],
                "react_goal": goal[:200],
            }
        )
        return state


Registry.register_agent(ReActAgent())
