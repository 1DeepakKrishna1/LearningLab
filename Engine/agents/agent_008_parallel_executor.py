"""agent-008 – Parallel Executor Agent."""

import concurrent.futures
from typing import Any, Dict, List

from agents._base_impl import AgentMixin
from core.registry import Registry


class ParallelExecutorAgent(AgentMixin):
    @property
    def agent_id(self) -> str:
        return "agent-008"

    def name(self) -> str:
        return "Parallel Executor"

    def description(self) -> str:
        return "Runs multiple sub-tasks concurrently to reduce total execution time"

    def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        cfg = state.get("current_node_config", {}).get("properties", {})
        max_concurrency = int(cfg.get("max_concurrency", 4))
        merge_strategy = cfg.get("merge_strategy", "combine")
        tool_ids: List[str] = state.get("current_node_config", {}).get("tools", [])

        from core.registry import Registry as _Reg

        def _run_one(tool_id: str) -> Dict[str, Any]:
            tool = _Reg.get_tool(tool_id)
            if tool is None:
                return {"tool_id": tool_id, "error": "not_found"}
            return {"tool_id": tool_id, "output": tool.run(dict(state.get("current_data", {})))}

        with concurrent.futures.ThreadPoolExecutor(max_workers=max_concurrency) as ex:
            futures = {ex.submit(_run_one, tid): tid for tid in tool_ids}
            parallel_results = []
            for fut in concurrent.futures.as_completed(futures):
                parallel_results.append(fut.result())

        merged: Dict[str, Any] = {}
        if merge_strategy == "combine":
            for r in parallel_results:
                merged.update(r.get("output", {}))

        state["current_data"].update(
            {
                "parallel_results": parallel_results,
                "parallel_tasks_run": len(parallel_results),
                "merge_strategy": merge_strategy,
                "merged_output": merged,
            }
        )
        return state


Registry.register_agent(ParallelExecutorAgent())
