"""
Pattern 19 – Evaluation and Monitoring
=========================================
Continuous quality measurement is essential for production AI agents.
This pattern demonstrates:

  LLM-as-Judge   – use a separate LLM call to score responses against
                   a structured rubric (G-Eval style).

  A/B Comparison – compare two agent configurations on the same prompt
                   set; determine which performs better.

  Eval Suite     – run a battery of test cases and aggregate metrics.

  Drift Monitor  – track metric trends across consecutive runs and
                   alert when quality degrades beyond a threshold.

Evaluation rubric (per response):
  • Relevance      (0–10) – does the response address the prompt?
  • Accuracy       (0–10) – are facts correct and claims verifiable?
  • Completeness   (0–10) – is the response sufficiently thorough?
  • Clarity        (0–10) – is the language clear and well-structured?
  • Conciseness    (0–10) – does it avoid waffle and repetition?
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
import statistics
from dataclasses import dataclass, field
from typing import Any, Optional

from llm_client import GroqClient, FAST_MODEL
from patterns.base import BasePattern

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Evaluation rubric and types
# ---------------------------------------------------------------------------

RUBRIC_DIMENSIONS = ["relevance", "accuracy", "completeness", "clarity", "conciseness"]


@dataclass
class EvalScore:
    dimension: str
    score: float       # 0.0 – 10.0
    rationale: str


@dataclass
class EvalResult:
    prompt: str
    response: str
    scores: list[EvalScore] = field(default_factory=list)
    overall: float = 0.0
    judge_notes: str = ""

    @property
    def score_dict(self) -> dict[str, float]:
        return {s.dimension: s.score for s in self.scores}

    def pretty_scores(self) -> str:
        lines = [f"  Overall: {self.overall:.1f}/10"]
        for s in self.scores:
            bar = "█" * int(s.score) + "░" * (10 - int(s.score))
            lines.append(f"  {s.dimension:<14} {s.score:4.1f}/10  {bar}")
        return "\n".join(lines)


@dataclass
class EvalSuiteResult:
    test_cases: list[EvalResult] = field(default_factory=list)

    def aggregate(self) -> dict[str, float]:
        if not self.test_cases:
            return {}
        agg: dict[str, list[float]] = {d: [] for d in RUBRIC_DIMENSIONS + ["overall"]}
        for tc in self.test_cases:
            for s in tc.scores:
                agg[s.dimension].append(s.score)
            agg["overall"].append(tc.overall)
        return {dim: round(statistics.mean(vals), 2) for dim, vals in agg.items() if vals}


# ---------------------------------------------------------------------------
# LLM Judge
# ---------------------------------------------------------------------------

_JUDGE_SYSTEM = """\
You are an objective AI response evaluator.  Score the assistant's response
to the given prompt on these dimensions (0–10 each):
  relevance, accuracy, completeness, clarity, conciseness

Respond with JSON only:
{
  "relevance":    {"score": <int>, "rationale": "<one sentence>"},
  "accuracy":     {"score": <int>, "rationale": "<one sentence>"},
  "completeness": {"score": <int>, "rationale": "<one sentence>"},
  "clarity":      {"score": <int>, "rationale": "<one sentence>"},
  "conciseness":  {"score": <int>, "rationale": "<one sentence>"},
  "overall":      <float, weighted average>,
  "notes":        "<optional general notes>"
}
"""


class LLMJudge:
    """
    Scores an (prompt, response) pair against a structured rubric.

    Uses a separate LLM call with a judge persona to avoid
    self-evaluation bias.
    """

    def __init__(self, client: GroqClient) -> None:
        self.client = client

    async def evaluate(self, prompt: str, response: str) -> EvalResult:
        judge_input = (
            f"Prompt given to assistant:\n{prompt}\n\n"
            f"Assistant's response:\n{response}"
        )
        raw = await self.client.complete_text(
            judge_input,
            system=_JUDGE_SYSTEM,
            model=FAST_MODEL,
            temperature=0.0,
            max_tokens=500,
        )
        clean = re.sub(r"```(?:json)?\s*|\s*```", "", raw).strip()

        try:
            data = json.loads(clean)
        except json.JSONDecodeError:
            logger.warning("Judge JSON parse failed; using neutral scores")
            data = {d: {"score": 5, "rationale": "parse error"} for d in RUBRIC_DIMENSIONS}
            data["overall"] = 5.0
            data["notes"] = "evaluation parse failed"

        scores = [
            EvalScore(
                dimension=dim,
                score=float(data.get(dim, {}).get("score", 5)),
                rationale=data.get(dim, {}).get("rationale", ""),
            )
            for dim in RUBRIC_DIMENSIONS
        ]
        overall = float(data.get("overall", statistics.mean(s.score for s in scores)))

        return EvalResult(
            prompt=prompt,
            response=response,
            scores=scores,
            overall=overall,
            judge_notes=data.get("notes", ""),
        )


# ---------------------------------------------------------------------------
# A/B Comparator
# ---------------------------------------------------------------------------


@dataclass
class ABComparison:
    prompt: str
    response_a: str
    response_b: str
    score_a: float
    score_b: float
    winner: str      # "A", "B", or "tie"
    delta: float     # score_a - score_b


class ABComparator:
    """
    Compare two responses on the same prompt.

    Both responses are evaluated independently by the judge;
    the winner is determined by overall score.
    """

    def __init__(self, judge: LLMJudge) -> None:
        self.judge = judge

    async def compare(self, prompt: str, response_a: str, response_b: str) -> ABComparison:
        result_a, result_b = await asyncio.gather(
            self.judge.evaluate(prompt, response_a),
            self.judge.evaluate(prompt, response_b),
        )
        delta = result_a.overall - result_b.overall
        winner = "A" if delta > 0.5 else ("B" if delta < -0.5 else "tie")
        return ABComparison(
            prompt=prompt,
            response_a=response_a,
            response_b=response_b,
            score_a=result_a.overall,
            score_b=result_b.overall,
            winner=winner,
            delta=delta,
        )


# ---------------------------------------------------------------------------
# Drift monitor
# ---------------------------------------------------------------------------


@dataclass
class DriftAlert:
    dimension: str
    previous_avg: float
    current_avg: float
    delta: float
    threshold: float

    def __str__(self) -> str:
        direction = "↓ degraded" if self.delta < 0 else "↑ improved"
        return (
            f"[DRIFT] {self.dimension}: {self.previous_avg:.1f} → {self.current_avg:.1f} "
            f"({direction}, Δ={self.delta:+.1f}, threshold=±{self.threshold})"
        )


class DriftMonitor:
    """Track evaluation metrics across runs and surface regressions."""

    def __init__(self, threshold: float = 1.5) -> None:
        self.threshold = threshold
        self._history: list[dict[str, float]] = []

    def record(self, aggregated_scores: dict[str, float]) -> list[DriftAlert]:
        alerts: list[DriftAlert] = []
        if self._history:
            prev = self._history[-1]
            for dim, current in aggregated_scores.items():
                if dim in prev:
                    delta = current - prev[dim]
                    if abs(delta) >= self.threshold:
                        alerts.append(DriftAlert(
                            dimension=dim,
                            previous_avg=prev[dim],
                            current_avg=current,
                            delta=delta,
                            threshold=self.threshold,
                        ))
        self._history.append(dict(aggregated_scores))
        return alerts

    def trend(self) -> list[dict[str, float]]:
        return list(self._history)


# ---------------------------------------------------------------------------
# Test suite
# ---------------------------------------------------------------------------

_EVAL_SUITE: list[tuple[str, str]] = [
    (
        "Explain the difference between SQL and NoSQL databases.",
        "detailed_technical",
    ),
    (
        "What is REST and how does it differ from GraphQL?",
        "detailed_technical",
    ),
    (
        "Summarise the key benefits of containerisation with Docker.",
        "concise_practical",
    ),
]

_SYSTEM_CONFIGS = {
    "detailed_technical": (
        "You are a senior software engineer. Provide detailed, technically accurate "
        "explanations with concrete examples."
    ),
    "concise_practical": (
        "You are a practical developer advocate. Give concise, actionable answers "
        "with clear bullet points."
    ),
}


# ---------------------------------------------------------------------------
# Pattern
# ---------------------------------------------------------------------------


class EvaluationMonitoringPattern(BasePattern):
    """
    Demonstrates automated LLM evaluation and monitoring.

    Runs an eval suite, compares A/B configurations, and checks for
    quality drift using the DriftMonitor.
    """

    name = "19 · Evaluation and Monitoring"

    async def run(  # type: ignore[override]
        self,
        test_suite: Optional[list[tuple[str, str]]] = None,
    ) -> dict[str, Any]:
        self.print_header()

        if test_suite is None:
            test_suite = _EVAL_SUITE

        judge = LLMJudge(self.client)
        comparator = ABComparator(judge)
        drift_monitor = DriftMonitor(threshold=1.5)

        # ── Phase 1: Eval Suite ───────────────────────────────────────
        self.print_step("Phase 1 › Running Eval Suite", f"{len(test_suite)} test cases")
        suite_result = EvalSuiteResult()

        eval_tasks = []
        for prompt, config_key in test_suite:
            system = _SYSTEM_CONFIGS.get(config_key, "You are a helpful assistant.")
            eval_tasks.append(self._eval_case(prompt, system, judge))

        eval_results = await asyncio.gather(*eval_tasks)
        for res in eval_results:
            suite_result.test_cases.append(res)
            self.print_step(
                f"  Eval › {res.prompt[:60]}…",
                res.pretty_scores(),
            )

        aggregated = suite_result.aggregate()
        self.print_step(
            "Phase 1 › Aggregated Suite Scores",
            "\n".join(f"  {k:<14} {v:.2f}/10" for k, v in aggregated.items()),
        )

        # ── Phase 2: A/B Comparison ───────────────────────────────────
        ab_prompt = test_suite[0][0]
        self.print_step("Phase 2 › A/B Comparison", f"Prompt: {ab_prompt}")

        response_a = await self.client.complete_text(
            ab_prompt,
            system=_SYSTEM_CONFIGS["detailed_technical"],
            max_tokens=300,
        )
        response_b = await self.client.complete_text(
            ab_prompt,
            system=_SYSTEM_CONFIGS["concise_practical"],
            max_tokens=300,
        )

        ab = await comparator.compare(ab_prompt, response_a, response_b)
        self.print_step(
            "Phase 2 › A/B Result",
            f"Config A (detailed_technical): {ab.score_a:.1f}/10\n"
            f"Config B (concise_practical):  {ab.score_b:.1f}/10\n"
            f"Winner: Config {ab.winner}  (Δ={ab.delta:+.2f})",
        )

        # ── Phase 3: Drift simulation ─────────────────────────────────
        # Simulate a second run with slightly lower scores
        self.print_step("Phase 3 › Drift Monitor (simulating 2 runs)", "")
        drift_monitor.record(aggregated)

        # Simulate degraded run
        degraded = {k: max(0.0, v - 2.0) for k, v in aggregated.items()}
        alerts = drift_monitor.record(degraded)

        if alerts:
            self.print_step(
                "Phase 3 › Drift Alerts",
                "\n".join(str(a) for a in alerts),
            )
        else:
            self.print_step("Phase 3 › Drift Monitor", "No significant drift detected.")

        self.print_result(
            f"Eval suite: {len(suite_result.test_cases)} cases | "
            f"Avg overall: {aggregated.get('overall', 0):.1f}/10 | "
            f"A/B winner: Config {ab.winner}"
        )

        return {
            "suite_size": len(suite_result.test_cases),
            "aggregated_scores": aggregated,
            "ab_winner": ab.winner,
            "ab_scores": {"A": ab.score_a, "B": ab.score_b},
            "drift_alerts": [str(a) for a in alerts],
        }

    async def _eval_case(self, prompt: str, system: str, judge: LLMJudge) -> EvalResult:
        response = await self.client.complete_text(prompt, system=system, max_tokens=300)
        return await judge.evaluate(prompt, response)
