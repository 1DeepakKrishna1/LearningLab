"""
Pattern 11: Goal Setting and Monitoring
=========================================
Concept: The agent decomposes a high-level objective into SMART sub-goals,
executes improvement steps, measures progress against each goal's target metric,
and emits alerts when goals are off-track. It loops until all goals are achieved
or the max iteration count is reached.

Graph:  START → set_goals → execute_improvement → measure_metrics → check_goals
                                  ↑                                       |
                                  └──── (not done) ── adjust_goals ───────┘
                                                            |
                                                         (done) → END

Demo:   Improve a given messy Python code snippet across three SMART goals:
        (1) complexity score ≤ 3, (2) docstring coverage = 100%, (3) bug-free.
"""
from __future__ import annotations

import re
import traceback
from typing import Annotated, Any, Dict, List
import operator

from langgraph.graph import StateGraph, START, END
from typing_extensions import TypedDict

from core.base import BasePattern, PatternResult
from core.llm import MODEL_LARGE, MODEL_SMALL

MAX_ITERATIONS = 4

INITIAL_CODE = """\
def calc(x,y,op):
    if op=='add':
        return x+y
    elif op=='sub':
        return x-y
    elif op == 'mul':
        return x*y
    elif op=='div':
        if y!=0:
            return x/y
    else:
        return None
"""


class GoalState(TypedDict):
    initial_task: str
    goals: List[Dict[str, Any]]   # [{"id","description","metric","target","current","achieved"}]
    code_artifact: str
    metrics: Dict[str, float]
    monitoring_log: Annotated[List[Dict], operator.add]
    adjustment_notes: str
    iteration: int
    goals_achieved: bool


class PatternGoalSettingMonitoring(BasePattern):
    PATTERN_NUMBER = 11
    PATTERN_NAME = "Goal Setting and Monitoring"
    DESCRIPTION = (
        "Decompose into SMART sub-goals, execute, measure, re-plan until goals are met."
    )

    # ------------------------------------------------------------------ metric helpers

    @staticmethod
    def _measure_complexity(code: str) -> float:
        """Approximate cyclomatic complexity by counting decision points."""
        keywords = ["if ", "elif ", "else:", "for ", "while ", "except", "and ", "or "]
        count = sum(code.count(k) for k in keywords)
        return float(count)

    @staticmethod
    def _measure_docstring_coverage(code: str) -> float:
        """Return fraction of functions/methods that have docstrings (0.0–1.0)."""
        import ast
        try:
            tree = ast.parse(code)
        except SyntaxError:
            return 0.0
        functions = [n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
        if not functions:
            return 1.0
        with_docs = sum(
            1 for f in functions
            if (f.body and isinstance(f.body[0], ast.Expr) and isinstance(f.body[0].value, ast.Constant))
        )
        return with_docs / len(functions)

    @staticmethod
    def _measure_bug_score(code: str) -> float:
        """Return 0.0 (bug-free) or 1.0 (has common bugs)."""
        bugs = ["return None", "except:\n", "bare except"]
        return 1.0 if any(b in code for b in bugs) else 0.0

    def _compute_metrics(self, code: str) -> Dict[str, float]:
        return {
            "complexity": self._measure_complexity(code),
            "docstring_coverage": self._measure_docstring_coverage(code),
            "bug_score": self._measure_bug_score(code),
        }

    def _check_all_goals(self, goals: List[Dict[str, Any]]) -> bool:
        return all(g["achieved"] for g in goals)

    # ------------------------------------------------------------------ nodes

    def _set_goals(self, state: GoalState) -> dict:
        goals = [
            {
                "id": "G1",
                "description": "Reduce cyclomatic complexity to ≤ 3 decision points",
                "metric": "complexity",
                "target": 3.0,
                "current": 0.0,
                "achieved": False,
                "direction": "lte",
            },
            {
                "id": "G2",
                "description": "Achieve 100% docstring coverage for all functions",
                "metric": "docstring_coverage",
                "target": 1.0,
                "current": 0.0,
                "achieved": False,
                "direction": "gte",
            },
            {
                "id": "G3",
                "description": "Eliminate common bug patterns (bare excepts, silent None returns)",
                "metric": "bug_score",
                "target": 0.0,
                "current": 0.0,
                "achieved": False,
                "direction": "lte",
            },
        ]
        metrics = self._compute_metrics(state["code_artifact"])
        return {
            "goals": goals,
            "metrics": metrics,
            "monitoring_log": [{"event": "goals_set", "count": len(goals), "initial_metrics": metrics}],
        }

    def _execute_improvement(self, state: GoalState) -> dict:
        unmet = [g for g in state["goals"] if not g["achieved"]]
        improvements_needed = "\n".join(
            f"- {g['id']}: {g['description']} (current={state['metrics'].get(g['metric'], '?')}, target={g['target']})"
            for g in unmet
        )
        prompt = (
            f"Improve this Python code to meet the following quality goals:\n"
            f"{improvements_needed}\n\n"
            f"{'Guidance: ' + state['adjustment_notes'] if state['adjustment_notes'] else ''}\n\n"
            f"Current code:\n```python\n{state['code_artifact']}\n```\n\n"
            "Return ONLY the improved Python code inside triple backticks, nothing else."
        )
        raw = self.llm.simple_prompt(prompt, model=MODEL_LARGE, max_tokens=600)
        match = re.search(r"```(?:python)?\n(.*?)```", raw, re.DOTALL)
        new_code = match.group(1).strip() if match else raw.strip()
        return {
            "code_artifact": new_code,
            "monitoring_log": [{
                "event": "improvement_executed",
                "iteration": state["iteration"] + 1,
                "goals_targeted": [g["id"] for g in unmet],
            }],
        }

    def _measure_metrics(self, state: GoalState) -> dict:
        metrics = self._compute_metrics(state["code_artifact"])
        return {
            "metrics": metrics,
            "monitoring_log": [{
                "event": "metrics_measured",
                "iteration": state["iteration"],
                "metrics": metrics,
            }],
        }

    def _check_goals(self, state: GoalState) -> str:
        metrics = state["metrics"]
        updated_goals = []
        for g in state["goals"]:
            current = metrics.get(g["metric"], 0.0)
            achieved = (current <= g["target"]) if g["direction"] == "lte" else (current >= g["target"])
            updated_goals.append({**g, "current": current, "achieved": achieved})

        all_done = self._check_all_goals(updated_goals)
        # Store updated goals back (via side-effect returned in dict below)
        # We'll return via a helper node
        self._pending_goals_update = updated_goals
        self._pending_all_done = all_done

        if all_done or state["iteration"] >= MAX_ITERATIONS:
            return "done"
        return "adjust"

    def _apply_goal_update(self, state: GoalState) -> dict:
        """Update goals and iteration counter — called before routing decision."""
        metrics = state["metrics"]
        updated_goals = []
        for g in state["goals"]:
            current = metrics.get(g["metric"], 0.0)
            achieved = (current <= g["target"]) if g["direction"] == "lte" else (current >= g["target"])
            updated_goals.append({**g, "current": current, "achieved": achieved})

        all_done = self._check_all_goals(updated_goals)
        return {
            "goals": updated_goals,
            "goals_achieved": all_done,
            "iteration": state["iteration"] + 1,
            "monitoring_log": [{
                "event": "goals_evaluated",
                "iteration": state["iteration"] + 1,
                "achieved": [g["id"] for g in updated_goals if g["achieved"]],
                "unmet": [g["id"] for g in updated_goals if not g["achieved"]],
            }],
        }

    def _should_continue(self, state: GoalState) -> str:
        if state["goals_achieved"] or state["iteration"] >= MAX_ITERATIONS:
            return "done"
        return "adjust"

    def _adjust_goals(self, state: GoalState) -> dict:
        unmet = [g for g in state["goals"] if not g["achieved"]]
        notes = "; ".join(
            f"{g['id']} needs {g['description']} (current={g['current']:.2f})"
            for g in unmet
        )
        return {
            "adjustment_notes": notes,
            "monitoring_log": [{"event": "adjustment", "notes": notes[:200]}],
        }

    # --------------------------------------------------------------- graph

    def build_graph(self) -> StateGraph:
        graph = StateGraph(GoalState)

        graph.add_node("set_goals", self._set_goals)
        graph.add_node("execute_improvement", self._execute_improvement)
        graph.add_node("measure_metrics", self._measure_metrics)
        graph.add_node("apply_goal_update", self._apply_goal_update)
        graph.add_node("adjust_goals", self._adjust_goals)

        graph.add_edge(START, "set_goals")
        graph.add_edge("set_goals", "execute_improvement")
        graph.add_edge("execute_improvement", "measure_metrics")
        graph.add_edge("measure_metrics", "apply_goal_update")
        graph.add_conditional_edges(
            "apply_goal_update",
            self._should_continue,
            {"adjust": "adjust_goals", "done": END},
        )
        graph.add_edge("adjust_goals", "execute_improvement")

        return graph.compile()

    # --------------------------------------------------------------- run

    def run(self, input_data: str, **kwargs) -> PatternResult:
        try:
            app = self.build_graph()
            initial_code = kwargs.get("code", INITIAL_CODE)
            initial: GoalState = {
                "initial_task": input_data,
                "goals": [],
                "code_artifact": initial_code,
                "metrics": {},
                "monitoring_log": [],
                "adjustment_notes": "",
                "iteration": 0,
                "goals_achieved": False,
            }
            final, elapsed_ms = self._timed_run(app.invoke, initial)
            return self._make_result(
                success=True,
                input_data=input_data,
                output_data=final["code_artifact"],
                elapsed_ms=elapsed_ms,
                steps=final["monitoring_log"],
                metadata={
                    "goals_achieved": final["goals_achieved"],
                    "total_iterations": final["iteration"],
                    "final_metrics": final["metrics"],
                    "goal_status": [
                        {"id": g["id"], "achieved": g["achieved"], "current": g.get("current")}
                        for g in final["goals"]
                    ],
                },
            )
        except Exception:
            return self._make_result(
                success=False,
                input_data=input_data,
                output_data=None,
                error=traceback.format_exc(),
            )
