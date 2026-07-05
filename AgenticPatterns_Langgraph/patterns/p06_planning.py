"""
Pattern 06: Planning
====================
Concept: The agent first generates a structured multi-step plan, then executes
each step sequentially, carrying context forward. A completion check node
decides whether to loop back and execute the next step or finalise.

Graph:  START → create_plan → execute_step → check_completion
                                 ↑                   |
                                 └── (more steps) ───┘
                                                     |
                                         (done) → synthesize → END

Demo:   "Design and build a Python CLI tool that monitors system CPU and memory
         usage and logs alerts when thresholds are exceeded."
"""
from __future__ import annotations

import json
import re
import traceback
from typing import Annotated, Any, Dict, List
import operator

from langgraph.graph import StateGraph, START, END
from typing_extensions import TypedDict

from core.base import BasePattern, PatternResult
from core.llm import MODEL_LARGE, MODEL_SMALL


class PlanState(TypedDict):
    goal: str
    plan: List[Dict[str, str]]          # [{"id": "1", "task": "...", "status": "pending"}]
    current_task_index: int
    completed_tasks: Annotated[List[Dict[str, Any]], operator.add]
    execution_log: Annotated[List[str], operator.add]
    final_output: str


class PatternPlanning(BasePattern):
    PATTERN_NUMBER = 6
    PATTERN_NAME = "Planning"
    DESCRIPTION = (
        "Decompose a goal into a plan, then execute each step sequentially."
    )

    # ------------------------------------------------------------------ nodes

    def _create_plan(self, state: PlanState) -> dict:
        prompt = (
            f"You are a senior software architect. Break the following goal into "
            f"5–7 concrete, actionable implementation steps.\n\n"
            f"Goal: {state['goal']}\n\n"
            "Return ONLY a JSON array of objects with keys 'id' (string '1','2',…) "
            "and 'task' (one-sentence description). Example:\n"
            '[{"id":"1","task":"..."},{"id":"2","task":"..."}]'
        )
        raw = self.llm.simple_prompt(prompt, model=MODEL_LARGE, max_tokens=512)

        plan: List[Dict[str, str]] = []
        match = re.search(r"\[.*\]", raw, re.DOTALL)
        if match:
            try:
                parsed = json.loads(match.group())
                plan = [
                    {"id": str(item.get("id", i + 1)), "task": item.get("task", ""), "status": "pending"}
                    for i, item in enumerate(parsed)
                ]
            except json.JSONDecodeError:
                pass

        if not plan:
            # Fallback: number each line
            lines = [l.strip() for l in raw.split("\n") if l.strip() and l.strip()[0].isdigit()]
            plan = [{"id": str(i + 1), "task": l.lstrip("0123456789.-) "), "status": "pending"} for i, l in enumerate(lines[:7])]

        return {
            "plan": plan,
            "current_task_index": 0,
            "execution_log": [f"Plan created with {len(plan)} steps"],
        }

    def _execute_step(self, state: PlanState) -> dict:
        idx = state["current_task_index"]
        task = state["plan"][idx]
        prior_context = "\n".join(
            f"Step {t['id']}: {t['result'][:200]}"
            for t in state["completed_tasks"]
        ) if state["completed_tasks"] else "No prior steps."

        prompt = (
            f"Goal: {state['goal']}\n\n"
            f"Prior completed steps:\n{prior_context}\n\n"
            f"Current step {task['id']}: {task['task']}\n\n"
            "Execute this step. Provide the concrete output (code snippet, design "
            "decision, configuration, or detailed instructions). Be specific."
        )
        result = self.llm.simple_prompt(prompt, model=MODEL_LARGE, max_tokens=600)

        completed = {
            "id": task["id"],
            "task": task["task"],
            "result": result,
            "status": "done",
        }
        # Mark task as done in the plan list
        updated_plan = list(state["plan"])
        updated_plan[idx] = {**task, "status": "done"}

        return {
            "plan": updated_plan,
            "completed_tasks": [completed],
            "execution_log": [f"Step {task['id']} completed: {task['task'][:60]}…"],
        }

    def _check_completion(self, state: PlanState) -> str:
        next_idx = state["current_task_index"] + 1
        if next_idx < len(state["plan"]):
            return "next_step"
        return "synthesize"

    def _advance_index(self, state: PlanState) -> dict:
        return {"current_task_index": state["current_task_index"] + 1}

    def _synthesize_output(self, state: PlanState) -> dict:
        steps_summary = "\n".join(
            f"### Step {t['id']}: {t['task']}\n{t['result']}"
            for t in state["completed_tasks"]
        )
        prompt = (
            f"Goal: {state['goal']}\n\n"
            f"All completed steps:\n{steps_summary}\n\n"
            "Write a cohesive final summary that integrates all steps into a "
            "complete implementation guide. Highlight the key code, decisions, "
            "and next actions. ~300 words."
        )
        final = self.llm.simple_prompt(prompt, model=MODEL_LARGE, max_tokens=700)
        return {
            "final_output": final,
            "execution_log": ["Synthesis complete"],
        }

    # --------------------------------------------------------------- graph

    def build_graph(self) -> StateGraph:
        graph = StateGraph(PlanState)

        graph.add_node("create_plan", self._create_plan)
        graph.add_node("execute_step", self._execute_step)
        graph.add_node("advance_index", self._advance_index)
        graph.add_node("synthesize", self._synthesize_output)

        graph.add_edge(START, "create_plan")
        graph.add_edge("create_plan", "execute_step")
        graph.add_conditional_edges(
            "execute_step",
            self._check_completion,
            {"next_step": "advance_index", "synthesize": "synthesize"},
        )
        graph.add_edge("advance_index", "execute_step")
        graph.add_edge("synthesize", END)

        return graph.compile()

    # --------------------------------------------------------------- run

    def run(self, input_data: str, **kwargs) -> PatternResult:
        try:
            app = self.build_graph()
            initial: PlanState = {
                "goal": input_data,
                "plan": [],
                "current_task_index": 0,
                "completed_tasks": [],
                "execution_log": [],
                "final_output": "",
            }
            final, elapsed_ms = self._timed_run(app.invoke, initial)
            return self._make_result(
                success=True,
                input_data=input_data,
                output_data=final["final_output"],
                elapsed_ms=elapsed_ms,
                steps=[{"step": t["id"], "task": t["task"], "status": t["status"]} for t in final["completed_tasks"]],
                metadata={
                    "plan_size": len(final["plan"]),
                    "execution_log": final["execution_log"],
                },
            )
        except Exception:
            return self._make_result(
                success=False,
                input_data=input_data,
                output_data=None,
                error=traceback.format_exc(),
            )
