"""
Pattern 16 – Resource-Aware Optimization
==========================================
Production agents operate within real constraints: token budgets,
API-call quotas, latency SLAs, and cost ceilings.  A resource-aware
agent monitors its own consumption and dynamically adapts its
strategy to stay within budget while maximising output quality.

Optimisation axes:
  • Token budget    – total input + output tokens allowed
  • Call budget     – maximum number of API round-trips
  • Time budget     – wall-clock seconds allowed
  • Cost budget     – estimated USD spend ceiling

Adaptive strategies (triggered when a budget falls below threshold):
  ┌─────────────────────┬────────────────────────────────────────┐
  │ Budget remaining    │ Strategy                               │
  ├─────────────────────┼────────────────────────────────────────┤
  │ > 60%              │ Default model, full quality            │
  │ 30 – 60%           │ Reduce max_tokens per call             │
  │ 10 – 30%           │ Switch to FAST_MODEL                   │
  │ < 10%              │ Summarise & skip non-essential steps   │
  └─────────────────────┴────────────────────────────────────────┘

Demo:  Summarise a long multi-topic document under a strict token
       budget, showing real-time budget reporting and strategy shifts.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Optional

from llm_client import GroqClient, LLMResponse, DEFAULT_MODEL, FAST_MODEL
from patterns.base import BasePattern

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Cost table  (approximate USD per 1M tokens, as of early 2025)
# ---------------------------------------------------------------------------

_COST_PER_M_TOKENS: dict[str, tuple[float, float]] = {
    DEFAULT_MODEL: (0.59, 0.79),   # (input, output) per 1M tokens
    FAST_MODEL:    (0.05, 0.08),
}


def estimate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    rates = _COST_PER_M_TOKENS.get(model, (0.59, 0.79))
    return (input_tokens * rates[0] + output_tokens * rates[1]) / 1_000_000


# ---------------------------------------------------------------------------
# Resource budget
# ---------------------------------------------------------------------------


@dataclass
class ResourceBudget:
    """Tracks allowed resources and their current consumption."""

    token_limit: int   = 8_000   # total tokens (in + out)
    call_limit: int    = 10      # API round-trips
    time_limit_s: float= 120.0   # seconds
    cost_limit_usd: float = 0.02 # USD

    tokens_used: int    = 0
    calls_made: int     = 0
    cost_usd: float     = 0.0
    start_time: float   = field(default_factory=time.perf_counter)

    def record(self, response: LLMResponse) -> None:
        self.tokens_used += response.total_tokens
        self.calls_made  += 1
        self.cost_usd    += estimate_cost(response.model, response.prompt_tokens, response.completion_tokens)

    @property
    def elapsed_s(self) -> float:
        return time.perf_counter() - self.start_time

    def remaining_pct(self) -> dict[str, float]:
        return {
            "tokens": max(0.0, 1 - self.tokens_used / max(self.token_limit, 1)),
            "calls":  max(0.0, 1 - self.calls_made  / max(self.call_limit,  1)),
            "time":   max(0.0, 1 - self.elapsed_s   / max(self.time_limit_s, 1)),
            "cost":   max(0.0, 1 - self.cost_usd    / max(self.cost_limit_usd, 1e-9)),
        }

    def most_constrained(self) -> tuple[str, float]:
        """Return the most-constrained resource and its remaining fraction."""
        rem = self.remaining_pct()
        axis = min(rem, key=rem.get)  # type: ignore[arg-type]
        return axis, rem[axis]

    def is_exhausted(self) -> bool:
        return any(v <= 0.0 for v in self.remaining_pct().values())

    def summary(self) -> str:
        rem = self.remaining_pct()
        return (
            f"Tokens: {self.tokens_used:>5}/{self.token_limit} "
            f"({rem['tokens']*100:.0f}% left)  |  "
            f"Calls: {self.calls_made}/{self.call_limit}  |  "
            f"Time: {self.elapsed_s:.1f}s/{self.time_limit_s}s  |  "
            f"Cost: ${self.cost_usd:.5f}/${self.cost_limit_usd:.3f}"
        )


# ---------------------------------------------------------------------------
# Adaptive configuration
# ---------------------------------------------------------------------------


@dataclass
class CallConfig:
    model: str
    max_tokens: int
    strategy_label: str


def choose_strategy(budget: ResourceBudget) -> CallConfig:
    """Select model and token limits based on remaining budget."""
    _, min_rem = budget.most_constrained()

    if min_rem > 0.60:
        return CallConfig(DEFAULT_MODEL, 600, "full_quality")
    if min_rem > 0.30:
        return CallConfig(DEFAULT_MODEL, 300, "reduced_tokens")
    if min_rem > 0.10:
        return CallConfig(FAST_MODEL,    250, "fast_model")
    return CallConfig(FAST_MODEL,        150, "minimal_degraded")


# ---------------------------------------------------------------------------
# Resource-aware client wrapper
# ---------------------------------------------------------------------------


class ResourceAwareClient:
    """
    Wraps GroqClient to enforce budget constraints and adapt strategy.

    Every call goes through ``complete_budgeted()``, which:
      1. Checks if budget is already exhausted (raises BudgetExhaustedError).
      2. Selects the appropriate strategy.
      3. Makes the API call.
      4. Records usage against the budget.
    """

    def __init__(self, client: GroqClient, budget: ResourceBudget) -> None:
        self.client = client
        self.budget = budget
        self.strategy_log: list[str] = []

    async def complete_budgeted(
        self,
        prompt: str,
        *,
        system: Optional[str] = None,
        force_strategy: Optional[CallConfig] = None,
    ) -> tuple[str, CallConfig]:
        """
        Execute a completion within budget constraints.

        Returns:
            (text_response, strategy_used)

        Raises:
            BudgetExhaustedError if budget is already exhausted.
        """
        if self.budget.is_exhausted():
            raise BudgetExhaustedError("All resource budgets exhausted.")

        cfg = force_strategy or choose_strategy(self.budget)
        self.strategy_log.append(cfg.strategy_label)

        response = await self.client.complete_text(
            prompt,
            system=system,
            model=cfg.model,
            max_tokens=cfg.max_tokens,
        )
        # We need the full LLMResponse to record tokens — use complete() instead
        # Re-call with complete() for proper tracking
        from llm_client import Message
        msgs = []
        if system:
            msgs.append(Message(role="system", content=system))
        msgs.append(Message(role="user", content=prompt))
        full_response = await self.client.complete(
            msgs, model=cfg.model, max_tokens=cfg.max_tokens
        )
        self.budget.record(full_response)
        return full_response.content, cfg


class BudgetExhaustedError(Exception):
    pass


# ---------------------------------------------------------------------------
# Pattern
# ---------------------------------------------------------------------------


_TOPICS = [
    ("Quantum Computing",      "Explain quantum superposition and entanglement and their role in computing."),
    ("Blockchain",             "Describe how consensus mechanisms work in distributed ledgers."),
    ("Neural Architecture",    "Explain attention mechanisms and transformers at a conceptual level."),
    ("Edge AI",                "Discuss the trade-offs of running inference on edge devices vs the cloud."),
    ("Federated Learning",     "Explain privacy-preserving machine learning with federated approaches."),
]


class ResourceOptimizationPattern(BasePattern):
    """
    Demonstrates resource-aware adaptive optimisation.

    The agent processes a sequence of tasks under a strict budget.
    As resources deplete, it automatically shifts to faster/cheaper
    strategies while reporting live budget status.
    """

    name = "16 · Resource-Aware Optimization"

    async def run(  # type: ignore[override]
        self,
        topics: Optional[list[tuple[str, str]]] = None,
        token_limit: int = 5_000,
        call_limit: int = 8,
    ) -> dict[str, Any]:
        self.print_header()

        if topics is None:
            topics = _TOPICS

        budget = ResourceBudget(
            token_limit=token_limit,
            call_limit=call_limit,
            time_limit_s=180.0,
            cost_limit_usd=0.015,
        )
        ra_client = ResourceAwareClient(self.client, budget)

        print(f"Initial budget: {budget.summary()}\n")

        results: list[dict[str, Any]] = []
        skipped = 0

        for i, (title, prompt) in enumerate(topics, start=1):
            if budget.is_exhausted():
                self.print_step(f"Task {i} › {title}", "[SKIPPED — budget exhausted]")
                skipped += 1
                continue

            cfg = choose_strategy(budget)
            self.print_step(
                f"Task {i} › {title}  [strategy: {cfg.strategy_label}]",
                f"Budget: {budget.summary()}",
            )

            try:
                text, used_cfg = await ra_client.complete_budgeted(
                    prompt,
                    system="You are a concise technical explainer. Be direct and specific.",
                )
            except BudgetExhaustedError:
                self.print_step(f"Task {i} › {title}", "[SKIPPED — budget exhausted mid-run]")
                skipped += 1
                continue

            self.print_step(f"Task {i} › Response  [model: {used_cfg.model.split('-')[0:3]}]", text)
            results.append({
                "title": title,
                "strategy": used_cfg.strategy_label,
                "model": used_cfg.model,
                "response_preview": text[:100] + "…",
            })

        # ── Final report ──────────────────────────────────────────────
        final_summary = budget.summary()
        strategy_distribution = {}
        for s in ra_client.strategy_log:
            strategy_distribution[s] = strategy_distribution.get(s, 0) + 1

        self.print_step(
            "Resource Usage Report",
            f"{final_summary}\n\n"
            f"Strategy distribution: {strategy_distribution}\n"
            f"Tasks completed: {len(results)}  |  Skipped: {skipped}",
        )
        self.print_result(
            f"Completed {len(results)}/{len(topics)} tasks | "
            f"Total tokens: {budget.tokens_used} | "
            f"Estimated cost: ${budget.cost_usd:.5f}"
        )
        return {
            "tasks_completed": len(results),
            "tasks_skipped": skipped,
            "tokens_used": budget.tokens_used,
            "calls_made": budget.calls_made,
            "cost_usd": round(budget.cost_usd, 6),
            "strategy_distribution": strategy_distribution,
            "results": results,
        }
