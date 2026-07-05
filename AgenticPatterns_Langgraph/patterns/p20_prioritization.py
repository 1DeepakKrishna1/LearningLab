"""
Pattern 20: Prioritization
============================
Concept: Assign urgency and importance scores to a queue of tasks, classify
them using the Eisenhower matrix, sort by a weighted priority formula, and
execute in optimal order — skipping deprioritised tasks when time is limited.

Eisenhower matrix:
  Q1 (urgent + important)     → DO NOW
  Q2 (not urgent + important) → SCHEDULE
  Q3 (urgent + not important) → DELEGATE
  Q4 (not urgent + not important) → ELIMINATE

Priority score = urgency × 0.6 + importance × 0.4  (both 1–5)

Graph:  START → analyse_tasks → classify_matrix → sort_queue → pick_next
              → execute_task → check_queue
                  ↑                  |
                  └── (more tasks) ──┘
                                     |
                               (empty/done) → generate_summary → END

Demo:   8 tasks with different urgency/importance profiles — show reordering
        and how Q4 tasks are eliminated from execution.
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

DEMO_TASKS = [
    {"id": "T1", "description": "Fix critical production bug causing data loss", "urgency": 5, "importance": 5},
    {"id": "T2", "description": "Update developer documentation", "urgency": 1, "importance": 3},
    {"id": "T3", "description": "Respond to angry enterprise customer complaint", "urgency": 5, "importance": 3},
    {"id": "T4", "description": "Design next-quarter product roadmap", "urgency": 2, "importance": 5},
    {"id": "T5", "description": "Attend optional team social event", "urgency": 2, "importance": 1},
    {"id": "T6", "description": "Apply security patch for known CVE", "urgency": 4, "importance": 5},
    {"id": "T7", "description": "Reorganise shared file storage folders", "urgency": 1, "importance": 1},
    {"id": "T8", "description": "Prepare quarterly board presentation", "urgency": 3, "importance": 5},
]


class PriorityState(TypedDict):
    raw_tasks: List[Dict[str, Any]]
    analysed_tasks: List[Dict[str, Any]]   # tasks with priority_score added
    priority_matrix: Dict[str, List[str]]  # quadrant → [task_ids]
    sorted_queue: List[Dict[str, Any]]     # sorted by priority score
    current_index: int
    completed_tasks: Annotated[List[Dict[str, Any]], operator.add]
    skipped_tasks: Annotated[List[Dict[str, Any]], operator.add]
    execution_log: Annotated[List[Dict], operator.add]
    summary: str


class PatternPrioritization(BasePattern):
    PATTERN_NUMBER = 20
    PATTERN_NAME = "Prioritization"
    DESCRIPTION = (
        "Eisenhower matrix classification + weighted scoring; execute in optimal order."
    )

    # ------------------------------------------------------------------ helpers

    @staticmethod
    def _priority_score(urgency: float, importance: float) -> float:
        return urgency * 0.6 + importance * 0.4

    @staticmethod
    def _classify_quadrant(urgency: int, importance: int) -> str:
        high_u = urgency >= 3
        high_i = importance >= 3
        if high_u and high_i:
            return "Q1_DO_NOW"
        elif not high_u and high_i:
            return "Q2_SCHEDULE"
        elif high_u and not high_i:
            return "Q3_DELEGATE"
        else:
            return "Q4_ELIMINATE"

    # ------------------------------------------------------------------ nodes

    def _analyse_tasks(self, state: PriorityState) -> dict:
        """Use LLM to validate/enrich urgency and importance scores."""
        task_list = "\n".join(
            f"{t['id']}: {t['description']} (urgency={t['urgency']}, importance={t['importance']})"
            for t in state["raw_tasks"]
        )
        prompt = (
            "Review the following tasks and their urgency/importance scores (1-5 scale). "
            "If any scores seem incorrect, adjust them. Return ONLY a JSON array with the same "
            "structure (id, urgency, importance fields). Keep descriptions unchanged.\n\n"
            f"Tasks:\n{task_list}\n\nJSON array:"
        )
        raw = self.llm.simple_prompt(prompt, model=MODEL_SMALL, max_tokens=400)

        analysed = list(state["raw_tasks"])  # default: use original
        match = re.search(r"\[.*\]", raw, re.DOTALL)
        if match:
            try:
                parsed = json.loads(match.group())
                updated = {item["id"]: item for item in parsed if "id" in item}
                analysed = [
                    {**t, **{k: updated[t["id"]][k] for k in ("urgency", "importance") if t["id"] in updated}}
                    for t in state["raw_tasks"]
                ]
            except (json.JSONDecodeError, KeyError):
                pass

        # Add priority score and quadrant
        for t in analysed:
            t["priority_score"] = round(self._priority_score(t["urgency"], t["importance"]), 2)
            t["quadrant"] = self._classify_quadrant(t["urgency"], t["importance"])

        return {
            "analysed_tasks": analysed,
            "execution_log": [{"event": "analysis_complete", "task_count": len(analysed)}],
        }

    def _classify_matrix(self, state: PriorityState) -> dict:
        matrix: Dict[str, List[str]] = {
            "Q1_DO_NOW": [], "Q2_SCHEDULE": [], "Q3_DELEGATE": [], "Q4_ELIMINATE": []
        }
        for t in state["analysed_tasks"]:
            q = t.get("quadrant", "Q4_ELIMINATE")
            matrix[q].append(t["id"])
        return {
            "priority_matrix": matrix,
            "execution_log": [{
                "event": "matrix_classified",
                **{q: ids for q, ids in matrix.items()},
            }],
        }

    def _sort_queue(self, state: PriorityState) -> dict:
        # Execute Q1 first, then Q2, then Q3; skip Q4
        quadrant_order = {"Q1_DO_NOW": 0, "Q2_SCHEDULE": 1, "Q3_DELEGATE": 2, "Q4_ELIMINATE": 3}
        sorted_tasks = sorted(
            state["analysed_tasks"],
            key=lambda t: (quadrant_order.get(t["quadrant"], 3), -t["priority_score"]),
        )
        return {
            "sorted_queue": sorted_tasks,
            "execution_log": [{
                "event": "queue_sorted",
                "order": [t["id"] for t in sorted_tasks],
            }],
        }

    def _execute_task(self, state: PriorityState) -> dict:
        idx = state["current_index"]
        task = state["sorted_queue"][idx]

        # Skip Q4 tasks
        if task["quadrant"] == "Q4_ELIMINATE":
            return {
                "skipped_tasks": [{"id": task["id"], "reason": "Q4 - eliminated from queue"}],
                "execution_log": [{
                    "event": "task_skipped",
                    "task_id": task["id"],
                    "quadrant": task["quadrant"],
                }],
            }

        prompt = (
            f"Execute the following task (be concrete and actionable):\n"
            f"Task: {task['description']}\n"
            f"Priority: {task['quadrant']} (score: {task['priority_score']})\n\n"
            "Provide a 2-3 sentence execution plan or immediate action."
        )
        result = self.llm.simple_prompt(prompt, model=MODEL_LARGE, max_tokens=200)

        completed = {
            "id": task["id"],
            "description": task["description"],
            "quadrant": task["quadrant"],
            "priority_score": task["priority_score"],
            "action_taken": result,
        }
        return {
            "completed_tasks": [completed],
            "execution_log": [{
                "event": "task_executed",
                "task_id": task["id"],
                "quadrant": task["quadrant"],
                "score": task["priority_score"],
            }],
        }

    def _check_queue(self, state: PriorityState) -> str:
        next_idx = state["current_index"] + 1
        if next_idx >= len(state["sorted_queue"]):
            return "done"
        return "next"

    def _advance_index(self, state: PriorityState) -> dict:
        return {"current_index": state["current_index"] + 1}

    def _generate_summary(self, state: PriorityState) -> dict:
        matrix = state["priority_matrix"]
        completed = state["completed_tasks"]
        skipped = state["skipped_tasks"]

        summary = (
            f"# Prioritization Summary\n\n"
            f"## Eisenhower Matrix\n"
            f"- Q1 (Do Now):      {', '.join(matrix['Q1_DO_NOW']) or 'none'}\n"
            f"- Q2 (Schedule):    {', '.join(matrix['Q2_SCHEDULE']) or 'none'}\n"
            f"- Q3 (Delegate):    {', '.join(matrix['Q3_DELEGATE']) or 'none'}\n"
            f"- Q4 (Eliminate):   {', '.join(matrix['Q4_ELIMINATE']) or 'none'}\n\n"
            f"## Execution Results\n"
            f"- Tasks executed: {len(completed)}\n"
            f"- Tasks eliminated: {len(skipped)}\n\n"
            f"## Top 3 Actions Taken\n"
        )
        for t in completed[:3]:
            summary += f"**{t['id']}** ({t['quadrant']}): {t['action_taken'][:100]}\n\n"

        return {"summary": summary}

    # --------------------------------------------------------------- graph

    def build_graph(self) -> StateGraph:
        graph = StateGraph(PriorityState)

        graph.add_node("analyse_tasks", self._analyse_tasks)
        graph.add_node("classify_matrix", self._classify_matrix)
        graph.add_node("sort_queue", self._sort_queue)
        graph.add_node("execute_task", self._execute_task)
        graph.add_node("advance_index", self._advance_index)
        graph.add_node("generate_summary", self._generate_summary)

        graph.add_edge(START, "analyse_tasks")
        graph.add_edge("analyse_tasks", "classify_matrix")
        graph.add_edge("classify_matrix", "sort_queue")
        graph.add_edge("sort_queue", "execute_task")
        graph.add_conditional_edges(
            "execute_task",
            self._check_queue,
            {"next": "advance_index", "done": "generate_summary"},
        )
        graph.add_edge("advance_index", "execute_task")
        graph.add_edge("generate_summary", END)

        return graph.compile()

    # --------------------------------------------------------------- run

    def run(self, input_data: str, **kwargs) -> PatternResult:
        try:
            app = self.build_graph()
            initial: PriorityState = {
                "raw_tasks": kwargs.get("tasks", DEMO_TASKS),
                "analysed_tasks": [],
                "priority_matrix": {},
                "sorted_queue": [],
                "current_index": 0,
                "completed_tasks": [],
                "skipped_tasks": [],
                "execution_log": [],
                "summary": "",
            }
            final, elapsed_ms = self._timed_run(app.invoke, initial)
            return self._make_result(
                success=True,
                input_data=input_data,
                output_data=final["summary"],
                elapsed_ms=elapsed_ms,
                steps=final["execution_log"],
                metadata={
                    "priority_matrix": final["priority_matrix"],
                    "completed": len(final["completed_tasks"]),
                    "skipped": len(final["skipped_tasks"]),
                    "execution_order": [t["id"] for t in final["sorted_queue"]],
                },
            )
        except Exception:
            return self._make_result(
                success=False,
                input_data=input_data,
                output_data=None,
                error=traceback.format_exc(),
            )
