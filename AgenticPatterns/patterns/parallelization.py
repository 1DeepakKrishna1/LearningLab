"""
Pattern 3 – Parallelization
=============================
Multiple independent LLM calls execute concurrently via
``asyncio.gather()``.  The results are collected and synthesised
into a unified response, reducing total wall-clock time compared to
sequential execution.

Demo workflow:
  Given a topic, three analyst personas evaluate it simultaneously:
    • Optimist  – highlights opportunities and benefits
    • Pessimist – identifies risks and downsides
    • Realist   – balanced, evidence-based perspective
  A final synthesis call combines all three perspectives.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from typing import Any

from llm_client import GroqClient
from patterns.base import BasePattern


@dataclass
class Perspective:
    persona: str
    content: str


@dataclass
class ParallelResult:
    topic: str
    perspectives: list[Perspective]
    synthesis: str
    elapsed_seconds: float


_PERSONAS: dict[str, str] = {
    "Optimist": (
        "You are an optimistic futurist. Highlight the exciting opportunities, "
        "benefits, and positive potential of the given topic. Be specific and enthusiastic."
    ),
    "Pessimist": (
        "You are a critical risk analyst. Identify the key risks, drawbacks, "
        "and potential pitfalls of the given topic. Be specific and rigorous."
    ),
    "Realist": (
        "You are a balanced analyst. Provide a grounded, evidence-based perspective "
        "on the given topic, acknowledging both positives and negatives. Be measured and precise."
    ),
}


class ParallelizationPattern(BasePattern):
    """
    Demonstrates fan-out/fan-in parallelization.

    Multiple LLM calls run concurrently; a synthesis step aggregates
    the results.  Elapsed time is reported to illustrate the speedup
    versus sequential execution.
    """

    name = "3 · Parallelization"

    async def _analyse(self, topic: str, persona: str, system: str) -> Perspective:
        content = await self.client.complete_text(
            f"Analyse this topic in 150–200 words: {topic}",
            system=system,
            max_tokens=350,
        )
        return Perspective(persona=persona, content=content)

    async def run(self, topic: str = "Large Language Models replacing software developers") -> ParallelResult:  # type: ignore[override]
        self.print_header()
        print(f"Topic: {topic}\n")

        start = time.perf_counter()

        # ── Fan-out: all perspectives in parallel ─────────────────────
        tasks = [
            self._analyse(topic, persona, system)
            for persona, system in _PERSONAS.items()
        ]
        perspectives: list[Perspective] = await asyncio.gather(*tasks)

        for p in perspectives:
            self.print_step(f"Perspective › {p.persona}", p.content)

        # ── Fan-in: synthesis ─────────────────────────────────────────
        combined = "\n\n".join(
            f"[{p.persona}]\n{p.content}" for p in perspectives
        )
        synthesis = await self.client.complete_text(
            f"Synthesise the following three perspectives on '{topic}' into a single, "
            f"balanced 200-word summary that captures all viewpoints:\n\n{combined}",
            system="You are an objective analyst who integrates multiple viewpoints.",
            max_tokens=400,
        )
        self.print_step("Synthesis (fan-in)", synthesis)

        elapsed = round(time.perf_counter() - start, 2)
        print(f"\n[Parallelization] All {len(perspectives)} LLM calls completed in {elapsed}s")

        result = ParallelResult(
            topic=topic,
            perspectives=perspectives,
            synthesis=synthesis,
            elapsed_seconds=elapsed,
        )
        self.print_result(synthesis)
        return result
