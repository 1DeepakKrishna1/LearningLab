"""
Pattern 19: Evaluation and Monitoring
=======================================
Concept: Every generated response is scored by an LLM-as-judge on multiple
dimensions. Scores below a threshold trigger automatic regeneration. All scores
are aggregated into a monitoring dashboard with trend analysis.

Evaluation dimensions (each 1–10):
  - Relevance   : does the response address the question?
  - Accuracy    : are the facts correct?
  - Coherence   : is the response logically structured?
  - Helpfulness : is it actionable and useful?
  - Safety      : is there any harmful content?

Graph:  START → generate_response → evaluate_response → check_threshold
              → [score < threshold AND retries < max] → regenerate → evaluate (loop)
              → update_dashboard → [more cases?] → generate_response (loop)
              → compile_report → END

Demo:   4 test cases spanning different question types; build a monitoring dashboard.
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

SCORE_THRESHOLD = 6.0    # min acceptable score (average across dimensions)
MAX_REGENERATIONS = 2

TEST_CASES = [
    {
        "question": "What are the main differences between Python lists and tuples?",
        "expected_type": "factual",
        "context": "Python programming",
    },
    {
        "question": "Explain quantum entanglement to a 10-year-old.",
        "expected_type": "explanation",
        "context": "Physics education",
    },
    {
        "question": "Write a haiku about distributed systems.",
        "expected_type": "creative",
        "context": "Software engineering",
    },
    {
        "question": "What is the best database for a high-traffic e-commerce site?",
        "expected_type": "recommendation",
        "context": "System architecture",
    },
]


class EvalState(TypedDict):
    test_cases: List[Dict[str, Any]]
    current_index: int
    current_response: str
    evaluation_scores: Dict[str, float]
    average_score: float
    regeneration_count: int
    all_evaluations: Annotated[List[Dict[str, Any]], operator.add]
    dashboard: Dict[str, Any]
    final_report: str


class PatternEvaluationMonitoring(BasePattern):
    PATTERN_NUMBER = 19
    PATTERN_NAME = "Evaluation and Monitoring"
    DESCRIPTION = (
        "LLM-as-judge scoring on 5 dimensions; auto-regeneration below threshold; dashboard."
    )

    # ------------------------------------------------------------------ nodes

    def _generate_response(self, state: EvalState) -> dict:
        case = state["test_cases"][state["current_index"]]
        regen_note = ""
        if state["regeneration_count"] > 0:
            prev_scores = state["evaluation_scores"]
            weak_dims = [d for d, s in prev_scores.items() if s < 6.0]
            regen_note = (
                f"\n\nIMPORTANT: Your previous response scored poorly on: {', '.join(weak_dims)}. "
                "Please specifically improve those aspects."
            )

        prompt = (
            f"Context: {case['context']}\n"
            f"Question type: {case['expected_type']}\n\n"
            f"Question: {case['question']}"
            f"{regen_note}"
        )
        response = self.llm.simple_prompt(prompt, model=MODEL_LARGE, max_tokens=400)
        return {"current_response": response}

    def _evaluate_response(self, state: EvalState) -> dict:
        case = state["test_cases"][state["current_index"]]
        eval_prompt = (
            f"You are a strict quality evaluator. Score the following AI response on each dimension from 1-10.\n\n"
            f"Question: {case['question']}\n"
            f"Expected type: {case['expected_type']}\n\n"
            f"Response to evaluate:\n{state['current_response']}\n\n"
            "Return ONLY a JSON object with these exact keys and integer scores:\n"
            '{"relevance": <1-10>, "accuracy": <1-10>, "coherence": <1-10>, '
            '"helpfulness": <1-10>, "safety": <1-10>}\n'
            "No other text."
        )
        raw = self.llm.simple_prompt(eval_prompt, model=MODEL_SMALL, max_tokens=100)

        # Parse scores
        scores: Dict[str, float] = {
            "relevance": 7.0, "accuracy": 7.0, "coherence": 7.0,
            "helpfulness": 7.0, "safety": 9.0,
        }
        match = re.search(r"\{[^{}]+\}", raw)
        if match:
            try:
                parsed = json.loads(match.group())
                scores = {
                    k: max(1.0, min(10.0, float(v)))
                    for k, v in parsed.items()
                    if k in scores
                }
            except (json.JSONDecodeError, ValueError):
                pass

        avg = sum(scores.values()) / len(scores)
        return {
            "evaluation_scores": scores,
            "average_score": round(avg, 2),
        }

    def _check_threshold(self, state: EvalState) -> str:
        if (
            state["average_score"] < SCORE_THRESHOLD
            and state["regeneration_count"] < MAX_REGENERATIONS
        ):
            return "regenerate"
        return "accept"

    def _increment_regen(self, state: EvalState) -> dict:
        return {"regeneration_count": state["regeneration_count"] + 1}

    def _update_dashboard(self, state: EvalState) -> dict:
        case = state["test_cases"][state["current_index"]]
        eval_record = {
            "case_index": state["current_index"],
            "question": case["question"][:60],
            "type": case["expected_type"],
            "response_preview": state["current_response"][:100],
            "scores": state["evaluation_scores"],
            "average": state["average_score"],
            "regenerations": state["regeneration_count"],
        }

        # Update dashboard aggregates
        dashboard = dict(state["dashboard"])
        all_evals = state["all_evaluations"] + [eval_record]
        if all_evals:
            for dim in ["relevance", "accuracy", "coherence", "helpfulness", "safety"]:
                dim_scores = [e["scores"].get(dim, 7.0) for e in all_evals]
                dashboard[f"avg_{dim}"] = round(sum(dim_scores) / len(dim_scores), 2)
            dashboard["total_cases"] = len(all_evals)
            dashboard["avg_score"] = round(sum(e["average"] for e in all_evals) / len(all_evals), 2)
            dashboard["total_regenerations"] = sum(e["regenerations"] for e in all_evals)
            dashboard["cases_below_threshold"] = sum(1 for e in all_evals if e["average"] < SCORE_THRESHOLD)

        next_index = state["current_index"] + 1
        return {
            "all_evaluations": [eval_record],
            "dashboard": dashboard,
            "current_index": next_index,
            "regeneration_count": 0,
            "current_response": "",
            "evaluation_scores": {},
            "average_score": 0.0,
        }

    def _has_more_cases(self, state: EvalState) -> str:
        if state["current_index"] < len(state["test_cases"]):
            return "more"
        return "done"

    def _compile_report(self, state: EvalState) -> dict:
        dash = state["dashboard"]
        evals = state["all_evaluations"]

        # Find best and worst cases
        if evals:
            best = max(evals, key=lambda e: e["average"])
            worst = min(evals, key=lambda e: e["average"])
        else:
            best = worst = {"question": "N/A", "average": 0}

        report = (
            f"# Evaluation and Monitoring Report\n\n"
            f"## Summary\n"
            f"- Total cases evaluated: {dash.get('total_cases', 0)}\n"
            f"- Average score: {dash.get('avg_score', 0):.2f}/10\n"
            f"- Cases below threshold ({SCORE_THRESHOLD}): {dash.get('cases_below_threshold', 0)}\n"
            f"- Total regenerations triggered: {dash.get('total_regenerations', 0)}\n\n"
            f"## Dimension Averages\n"
            + "\n".join(
                f"- {dim.title()}: {dash.get(f'avg_{dim}', 0):.2f}"
                for dim in ["relevance", "accuracy", "coherence", "helpfulness", "safety"]
            )
            + f"\n\n## Best Case\n"
            f"- Q: {best['question']}\n"
            f"- Score: {best['average']:.2f}\n\n"
            f"## Weakest Case\n"
            f"- Q: {worst['question']}\n"
            f"- Score: {worst['average']:.2f}"
        )
        return {"final_report": report}

    # --------------------------------------------------------------- graph

    def build_graph(self) -> StateGraph:
        graph = StateGraph(EvalState)

        graph.add_node("generate_response", self._generate_response)
        graph.add_node("evaluate_response", self._evaluate_response)
        graph.add_node("increment_regen", self._increment_regen)
        graph.add_node("update_dashboard", self._update_dashboard)
        graph.add_node("compile_report", self._compile_report)

        graph.add_edge(START, "generate_response")
        graph.add_edge("generate_response", "evaluate_response")
        graph.add_conditional_edges(
            "evaluate_response",
            self._check_threshold,
            {"regenerate": "increment_regen", "accept": "update_dashboard"},
        )
        graph.add_edge("increment_regen", "generate_response")
        graph.add_conditional_edges(
            "update_dashboard",
            self._has_more_cases,
            {"more": "generate_response", "done": "compile_report"},
        )
        graph.add_edge("compile_report", END)

        return graph.compile()

    # --------------------------------------------------------------- run

    def run(self, input_data: str, **kwargs) -> PatternResult:
        try:
            app = self.build_graph()
            initial: EvalState = {
                "test_cases": TEST_CASES,
                "current_index": 0,
                "current_response": "",
                "evaluation_scores": {},
                "average_score": 0.0,
                "regeneration_count": 0,
                "all_evaluations": [],
                "dashboard": {},
                "final_report": "",
            }
            final, elapsed_ms = self._timed_run(app.invoke, initial)
            return self._make_result(
                success=True,
                input_data=input_data,
                output_data=final["final_report"],
                elapsed_ms=elapsed_ms,
                steps=final["all_evaluations"],
                metadata={
                    "dashboard": final["dashboard"],
                    "threshold": SCORE_THRESHOLD,
                    "max_regenerations": MAX_REGENERATIONS,
                },
            )
        except Exception:
            return self._make_result(
                success=False,
                input_data=input_data,
                output_data=None,
                error=traceback.format_exc(),
            )
