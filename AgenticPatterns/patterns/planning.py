"""
Pattern 6 – Planning
======================
The LLM first creates an explicit, structured plan (a numbered list
of concrete steps) for a complex task, then executes each step
sequentially, maintaining a growing context window so later steps
can reference earlier results.

Demo workflow:
  Given a product idea, the planner:
    1. Decomposes the task into N actionable steps
    2. Executes each step in order, feeding prior outputs as context
    3. Produces a final consolidated deliverable
"""

from __future__ import annotations

import json
import re
import logging
from dataclasses import dataclass, field
from typing import Any

from llm_client import GroqClient
from patterns.base import BasePattern

logger = logging.getLogger(__name__)

_PLANNER_SYSTEM = """\
You are a strategic project planner. Given a goal, break it down into
clear, numbered, actionable steps (maximum 5 steps).

Respond with a JSON array of step descriptions only. Example:
["Step description 1", "Step description 2", "Step description 3"]
"""

_EXECUTOR_SYSTEM = """\
You are a diligent task executor. You will be given:
- The overall goal
- The specific step to execute
- Context from previously completed steps

Execute only the current step thoroughly (150–200 words). Be concrete and specific.
"""

_CONSOLIDATOR_SYSTEM = """\
You are a technical writer. Consolidate the provided step outputs into a single,
coherent, well-structured document. Ensure the result flows naturally and avoids
repetition.
"""


@dataclass
class ExecutedStep:
    number: int
    description: str
    output: str


@dataclass
class PlanningResult:
    goal: str
    plan: list[str] = field(default_factory=list)
    executed_steps: list[ExecutedStep] = field(default_factory=list)
    final_output: str = ""


class PlanningPattern(BasePattern):
    """
    Demonstrates LLM-driven task planning and execution.

    Phase 1 – Plan:    LLM decomposes the goal into ordered steps.
    Phase 2 – Execute: each step runs sequentially, accumulating context.
    Phase 3 – Consolidate: all step outputs merged into a final document.
    """

    name = "6 · Planning"

    async def _generate_plan(self, goal: str) -> list[str]:
        """Ask the LLM to produce a JSON list of step descriptions."""
        raw = await self.client.complete_text(
            f"Goal: {goal}",
            system=_PLANNER_SYSTEM,
            temperature=0.3,
            max_tokens=300,
        )
        # Extract JSON array from the response (handle markdown code fences)
        match = re.search(r"\[.*?\]", raw, re.DOTALL)
        if match:
            try:
                steps = json.loads(match.group())
                if isinstance(steps, list) and all(isinstance(s, str) for s in steps):
                    return steps
            except json.JSONDecodeError:
                pass
        # Fallback: split numbered lines
        logger.warning("Could not parse plan JSON, falling back to line-split")
        lines = [ln.strip() for ln in raw.splitlines() if ln.strip()]
        return [re.sub(r"^\d+[\.\)]\s*", "", ln) for ln in lines if ln]

    async def run(  # type: ignore[override]
        self,
        goal: str = (
            "Create a go-to-market strategy for a new AI-powered code review SaaS product"
        ),
    ) -> PlanningResult:
        self.print_header()
        print(f"Goal: {goal}\n")

        result = PlanningResult(goal=goal)

        # ── Phase 1: Plan ─────────────────────────────────────────────
        steps = await self._generate_plan(goal)
        result.plan = steps
        self.print_step("Phase 1 › Generated Plan", "\n".join(f"  {i+1}. {s}" for i, s in enumerate(steps)))

        # ── Phase 2: Execute each step ────────────────────────────────
        context_parts: list[str] = []

        for i, step_desc in enumerate(steps, start=1):
            context_summary = (
                "\n\n".join(
                    f"Step {es.number} output:\n{es.output}"
                    for es in result.executed_steps
                )
                or "No prior steps completed yet."
            )

            prompt = (
                f"Overall goal: {goal}\n\n"
                f"Current step ({i}/{len(steps)}): {step_desc}\n\n"
                f"Context from previous steps:\n{context_summary}\n\n"
                f"Execute this step now:"
            )
            output = await self.client.complete_text(
                prompt,
                system=_EXECUTOR_SYSTEM,
                max_tokens=400,
            )
            executed = ExecutedStep(number=i, description=step_desc, output=output)
            result.executed_steps.append(executed)
            context_parts.append(f"Step {i}: {step_desc}\n{output}")
            self.print_step(f"Phase 2 › Step {i}: {step_desc}", output)

        # ── Phase 3: Consolidate ──────────────────────────────────────
        all_outputs = "\n\n---\n\n".join(context_parts)
        final_output = await self.client.complete_text(
            f"Goal: {goal}\n\nStep outputs to consolidate:\n\n{all_outputs}",
            system=_CONSOLIDATOR_SYSTEM,
            max_tokens=800,
        )
        result.final_output = final_output
        self.print_step("Phase 3 › Consolidated Output", final_output)

        self.print_result(f"Plan executed in {len(steps)} steps.")
        return result
