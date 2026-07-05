"""
Pattern 16: Resource-Aware Optimization
==========================================
Concept: The agent monitors a multi-dimensional resource budget (tokens, latency,
cost) and dynamically selects the model tier, adjusts response depth, and skips
non-essential steps when budgets are nearly exhausted.

Resource tiers:
  - FULL    : large model, detailed response, full context
  - REDUCED : small model, concise response, trimmed context
  - MINIMAL : small model, 1-sentence answer, no context

Graph:  START → assess_resources → select_strategy → generate_answer
              → log_resource_usage → check_remaining
                      ↑                     |
                      └──── (more work) ────┘
                                            |
                                   (done / budget spent) → END

Demo:   Answer 5 questions with a combined token budget of 1200 and a cost
        budget of $0.01, showing how the agent degrades gracefully.
"""
from __future__ import annotations

import time
import traceback
from typing import Annotated, Any, Dict, List
import operator

from langgraph.graph import StateGraph, START, END
from typing_extensions import TypedDict

from core.base import BasePattern, PatternResult
from core.llm import MODEL_LARGE, MODEL_SMALL

# Approximate pricing (USD per 1K tokens)
COST_PER_1K = {MODEL_LARGE: 0.0009, MODEL_SMALL: 0.0001}

DEMO_QUESTIONS = [
    ("What is machine learning?", "easy"),
    ("Explain the difference between supervised and unsupervised learning with examples.", "medium"),
    ("Describe transformer architecture, attention mechanisms, and why they revolutionised NLP.", "hard"),
    ("What is gradient descent?", "easy"),
    ("How does reinforcement learning from human feedback (RLHF) work in LLM training?", "hard"),
]


class ResourceState(TypedDict):
    questions: List[Dict[str, str]]    # [{"question": ..., "difficulty": ...}]
    current_index: int
    token_budget: int
    tokens_used: int
    cost_budget_usd: float
    cost_used_usd: float
    latency_budget_ms: float
    latency_used_ms: float
    current_strategy: str              # "full" | "reduced" | "minimal"
    responses: Annotated[List[Dict[str, Any]], operator.add]
    resource_log: Annotated[List[Dict], operator.add]
    all_answered: bool


class PatternResourceAwareOptimization(BasePattern):
    PATTERN_NUMBER = 16
    PATTERN_NAME = "Resource-Aware Optimization"
    DESCRIPTION = (
        "Dynamic model/depth selection based on remaining token, cost, and latency budgets."
    )

    # ------------------------------------------------------------------ nodes

    def _assess_resources(self, state: ResourceState) -> dict:
        """Compute budget utilisation ratios and determine resource pressure."""
        token_ratio = state["tokens_used"] / max(state["token_budget"], 1)
        cost_ratio = state["cost_used_usd"] / max(state["cost_budget_usd"], 1e-9)
        latency_ratio = state["latency_used_ms"] / max(state["latency_budget_ms"], 1)

        pressure = max(token_ratio, cost_ratio, latency_ratio)

        if pressure < 0.5:
            strategy = "full"
        elif pressure < 0.8:
            strategy = "reduced"
        else:
            strategy = "minimal"

        return {
            "current_strategy": strategy,
            "resource_log": [{
                "event": "assessment",
                "index": state["current_index"],
                "token_utilization": round(token_ratio * 100, 1),
                "cost_utilization": round(cost_ratio * 100, 1),
                "latency_utilization": round(latency_ratio * 100, 1),
                "strategy_chosen": strategy,
            }],
        }

    def _select_strategy(self, state: ResourceState) -> dict:
        """Log the strategy decision (actual logic is in assess_resources)."""
        strategy = state["current_strategy"]
        q = state["questions"][state["current_index"]]

        if strategy == "full":
            model = MODEL_LARGE
            max_tok = 400
            depth = "Provide a detailed, thorough explanation."
        elif strategy == "reduced":
            model = MODEL_SMALL
            max_tok = 200
            depth = "Provide a concise but complete explanation in 2-3 sentences."
        else:   # minimal
            model = MODEL_SMALL
            max_tok = 80
            depth = "Answer in one sentence."

        return {
            "resource_log": [{
                "event": "strategy_applied",
                "model": model,
                "max_tokens": max_tok,
                "depth": depth,
                "question": q["question"][:60],
            }],
            "_current_model": model,
            "_current_max_tokens": max_tok,
            "_current_depth": depth,
        }

    def _generate_answer(self, state: ResourceState) -> dict:
        q = state["questions"][state["current_index"]]
        strategy = state["current_strategy"]

        if strategy == "full":
            model, max_tok = MODEL_LARGE, 400
            instruction = "Provide a detailed, thorough explanation with examples."
        elif strategy == "reduced":
            model, max_tok = MODEL_SMALL, 200
            instruction = "Provide a concise explanation in 2-3 sentences."
        else:
            model, max_tok = MODEL_SMALL, 80
            instruction = "Answer in one short sentence."

        t0 = time.perf_counter()
        answer = self.llm.simple_prompt(
            f"{instruction}\n\nQuestion: {q['question']}",
            model=model,
            max_tokens=max_tok,
        )
        elapsed = (time.perf_counter() - t0) * 1000

        # Estimate token usage (rough: 1 token ≈ 4 chars)
        prompt_chars = len(instruction) + len(q["question"])
        answer_chars = len(answer)
        tokens_est = (prompt_chars + answer_chars) // 4
        cost_est = tokens_est / 1000 * COST_PER_1K.get(model, 0.0005)

        return {
            "tokens_used": state["tokens_used"] + tokens_est,
            "cost_used_usd": state["cost_used_usd"] + cost_est,
            "latency_used_ms": state["latency_used_ms"] + elapsed,
            "responses": [{
                "index": state["current_index"],
                "question": q["question"],
                "difficulty": q["difficulty"],
                "strategy": strategy,
                "model": model,
                "answer": answer,
                "tokens_est": tokens_est,
                "cost_est_usd": round(cost_est, 6),
                "latency_ms": round(elapsed, 1),
            }],
        }

    def _log_resource_usage(self, state: ResourceState) -> dict:
        return {
            "resource_log": [{
                "event": "post_generation",
                "tokens_total": state["tokens_used"],
                "cost_total_usd": round(state["cost_used_usd"], 6),
                "latency_total_ms": round(state["latency_used_ms"], 1),
            }],
        }

    def _check_remaining(self, state: ResourceState) -> str:
        next_index = state["current_index"] + 1
        budget_exhausted = (
            state["tokens_used"] >= state["token_budget"] * 0.95
            or state["cost_used_usd"] >= state["cost_budget_usd"] * 0.95
        )
        if next_index >= len(state["questions"]) or budget_exhausted:
            return "done"
        return "next"

    def _advance_index(self, state: ResourceState) -> dict:
        return {"current_index": state["current_index"] + 1}

    # --------------------------------------------------------------- graph

    def build_graph(self) -> StateGraph:
        graph = StateGraph(ResourceState)

        graph.add_node("assess_resources", self._assess_resources)
        graph.add_node("select_strategy", self._select_strategy)
        graph.add_node("generate_answer", self._generate_answer)
        graph.add_node("log_resource_usage", self._log_resource_usage)
        graph.add_node("advance_index", self._advance_index)

        graph.add_edge(START, "assess_resources")
        graph.add_edge("assess_resources", "select_strategy")
        graph.add_edge("select_strategy", "generate_answer")
        graph.add_edge("generate_answer", "log_resource_usage")
        graph.add_conditional_edges(
            "log_resource_usage",
            self._check_remaining,
            {"next": "advance_index", "done": END},
        )
        graph.add_edge("advance_index", "assess_resources")

        return graph.compile()

    # --------------------------------------------------------------- run

    def run(self, input_data: str, **kwargs) -> PatternResult:
        try:
            app = self.build_graph()
            questions = [{"question": q, "difficulty": d} for q, d in DEMO_QUESTIONS]
            initial: ResourceState = {
                "questions": questions,
                "current_index": 0,
                "token_budget": kwargs.get("token_budget", 1200),
                "tokens_used": 0,
                "cost_budget_usd": kwargs.get("cost_budget", 0.01),
                "cost_used_usd": 0.0,
                "latency_budget_ms": kwargs.get("latency_budget_ms", 60_000),
                "latency_used_ms": 0.0,
                "current_strategy": "full",
                "responses": [],
                "resource_log": [],
                "all_answered": False,
            }
            final, elapsed_ms = self._timed_run(app.invoke, initial)
            summary = (
                f"Answered {len(final['responses'])}/{len(questions)} questions. "
                f"Tokens used: {final['tokens_used']}/{initial['token_budget']}. "
                f"Cost: ${final['cost_used_usd']:.5f}/${initial['cost_budget_usd']}. "
                f"Strategies used: {', '.join(sorted({r['strategy'] for r in final['responses']}))}"
            )
            return self._make_result(
                success=True,
                input_data=input_data,
                output_data=summary,
                elapsed_ms=elapsed_ms,
                steps=final["responses"],
                metadata={
                    "final_tokens_used": final["tokens_used"],
                    "final_cost_usd": round(final["cost_used_usd"], 6),
                    "strategies_applied": {r["strategy"] for r in final["responses"]},
                    "resource_log": final["resource_log"],
                },
            )
        except Exception:
            return self._make_result(
                success=False,
                input_data=input_data,
                output_data=None,
                error=traceback.format_exc(),
            )
