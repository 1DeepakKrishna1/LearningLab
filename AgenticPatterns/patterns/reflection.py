"""
Pattern 4 – Reflection
========================
The LLM generates an initial output, then acts as its own critic to
identify weaknesses, and finally produces an improved version based
on that self-critique.  This loop can run for N iterations.

Reflection loop used in this demo:
  1. Generate: produce initial Python function for the given task
  2. Critique:  review the function for correctness, edge cases,
                readability, and best practices
  3. Improve:   rewrite the function addressing all critique points
  (Optional: repeat steps 2–3 for deeper refinement)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from llm_client import GroqClient
from patterns.base import BasePattern


@dataclass
class ReflectionIteration:
    iteration: int
    code: str
    critique: str


@dataclass
class ReflectionResult:
    task: str
    initial_code: str = ""
    iterations: list[ReflectionIteration] = field(default_factory=list)
    final_code: str = ""


_GENERATOR_SYSTEM = (
    "You are an expert Python developer. Write clean, Pythonic code with type hints. "
    "Return only the code block, no prose."
)

_CRITIC_SYSTEM = (
    "You are a rigorous code reviewer. Analyse the provided Python code and list "
    "specific, actionable improvements covering: correctness, edge-case handling, "
    "readability, efficiency, and Python best practices. "
    "Number each issue. Be concise but precise."
)

_IMPROVER_SYSTEM = (
    "You are an expert Python developer. You will receive code and a critique. "
    "Rewrite the code addressing every critique point. "
    "Return only the improved code block, no prose."
)


class ReflectionPattern(BasePattern):
    """
    Demonstrates self-reflection and iterative improvement.

    The LLM generates code, critiques it, then rewrites to address
    the critique.  Supports multiple reflection iterations.
    """

    name = "4 · Reflection"

    async def run(  # type: ignore[override]
        self,
        task: str = "Write a Python function that finds all prime numbers up to N using the Sieve of Eratosthenes",
        iterations: int = 2,
    ) -> ReflectionResult:
        self.print_header()
        print(f"Task: {task}")
        print(f"Reflection iterations: {iterations}\n")

        result = ReflectionResult(task=task)

        # ── Step 1: Initial generation ────────────────────────────────
        initial_code = await self.client.complete_text(
            task,
            system=_GENERATOR_SYSTEM,
            max_tokens=600,
        )
        result.initial_code = initial_code
        self.print_step("Step 1 › Initial Code", initial_code)

        current_code = initial_code

        for i in range(1, iterations + 1):
            # ── Critique ──────────────────────────────────────────────
            critique = await self.client.complete_text(
                f"Review this Python code:\n\n{current_code}",
                system=_CRITIC_SYSTEM,
                max_tokens=500,
            )
            self.print_step(f"Iteration {i} › Critique", critique)

            # ── Improve ───────────────────────────────────────────────
            improved_code = await self.client.complete_text(
                f"Original code:\n{current_code}\n\nCritique:\n{critique}\n\n"
                f"Rewrite the code addressing all critique points.",
                system=_IMPROVER_SYSTEM,
                max_tokens=700,
            )
            self.print_step(f"Iteration {i} › Improved Code", improved_code)

            result.iterations.append(
                ReflectionIteration(
                    iteration=i,
                    code=improved_code,
                    critique=critique,
                )
            )
            current_code = improved_code

        result.final_code = current_code
        self.print_result(f"Final code after {iterations} reflection iteration(s):\n\n{result.final_code}")
        return result
