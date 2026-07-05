"""
Pattern 17 – Reasoning Techniques
====================================
Advanced reasoning strategies prompt the LLM to think more carefully,
explore multiple paths, and self-verify before committing to an answer.

Techniques implemented:
  CoT  – Chain-of-Thought:    "Think step by step" before answering.
  ToT  – Tree-of-Thought:     Generate N candidate solutions, evaluate
                               each, select the best branch.
  ReAct – Reason + Act:       Interleave Thought → Action → Observation
                               cycles (tool-augmented reasoning).
  SC   – Self-Consistency:    Sample N independent solutions at higher
                               temperature, aggregate via majority vote.

Each technique is applied to the same problem and results are compared
side-by-side, revealing differences in depth and accuracy.
"""

from __future__ import annotations

import asyncio
import logging
import re
from dataclasses import dataclass, field
from typing import Any, Optional

from llm_client import GroqClient, Message, FAST_MODEL
from patterns.base import BasePattern

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Shared problem (same input for all techniques)
# ---------------------------------------------------------------------------

DEFAULT_PROBLEM = (
    "A train travels from City A to City B at 60 km/h and returns at 40 km/h. "
    "What is the average speed for the entire round trip? "
    "Also explain why the naive average of (60+40)/2 = 50 km/h is wrong."
)


# ---------------------------------------------------------------------------
# 1. Chain-of-Thought (CoT)
# ---------------------------------------------------------------------------

_COT_SYSTEM = """\
You are a careful analytical reasoner.
Before giving your final answer, explicitly work through the problem
step by step, labelling each step.  Structure your response as:

Step 1: [reasoning]
Step 2: [reasoning]
...
Final Answer: [concise answer]
"""


async def chain_of_thought(client: GroqClient, problem: str) -> str:
    return await client.complete_text(
        problem,
        system=_COT_SYSTEM,
        temperature=0.3,
        max_tokens=600,
    )


# ---------------------------------------------------------------------------
# 2. Tree-of-Thought (ToT)
# ---------------------------------------------------------------------------

_TOT_GENERATOR_SYSTEM = """\
You are a problem solver generating ONE distinct solution approach.
Present your approach clearly with step-by-step reasoning.
Label it clearly: "Approach: [title]" then show the working.
"""

_TOT_EVALUATOR_SYSTEM = """\
You are an expert evaluator. You will see multiple solution approaches
to a problem. Score each approach 1–10 for correctness and clarity.
Then identify the BEST approach and explain why.

Output format:
Scores:
  Approach 1: [score]/10 — [brief reason]
  Approach 2: [score]/10 — [brief reason]
  ...
Best Approach: [number] — [justification]
Final Answer: [the correct answer derived from the best approach]
"""


async def tree_of_thought(client: GroqClient, problem: str, branches: int = 3) -> str:
    # Generate N branches in parallel
    branch_tasks = [
        client.complete_text(
            f"Solve this problem with a distinct approach (approach #{i+1} of {branches}):\n{problem}",
            system=_TOT_GENERATOR_SYSTEM,
            temperature=0.7,
            max_tokens=350,
        )
        for i in range(branches)
    ]
    branch_solutions = await asyncio.gather(*branch_tasks)

    # Evaluate and select best branch
    evaluation_input = "\n\n---\n\n".join(
        f"Approach {i+1}:\n{sol}" for i, sol in enumerate(branch_solutions)
    )
    evaluation = await client.complete_text(
        f"Problem: {problem}\n\nSolutions:\n{evaluation_input}",
        system=_TOT_EVALUATOR_SYSTEM,
        temperature=0.1,
        max_tokens=500,
    )
    return f"[Generated {branches} branches]\n\n{evaluation}"


# ---------------------------------------------------------------------------
# 3. ReAct (Reason + Act)
# ---------------------------------------------------------------------------

_REACT_SYSTEM = """\
You are a reasoning agent that solves problems using a structured loop.
For each step output EXACTLY one of:

  Thought: [your reasoning about what to do next]
  Action: [calculate | lookup | verify | conclude]
  Action Input: [input for the action]

After each Action/Action Input pair, I will provide:
  Observation: [result]

Continue the loop until you use Action: conclude.
Then output:
  Final Answer: [your answer]
"""

# Simulated "executor" for ReAct actions
_MATH_FACTS = {
    "harmonic mean formula": "For two speeds a and b: HM = 2ab/(a+b)",
    "arithmetic mean formula": "For two values: AM = (a+b)/2",
}


def _react_execute(action: str, action_input: str) -> str:
    """Simulate tool execution for ReAct actions."""
    action = action.strip().lower()
    if action == "calculate":
        import math
        allowed = {"__builtins__": {}, "sqrt": math.sqrt, "pi": math.pi}
        try:
            return str(eval(action_input.strip(), allowed, {}))  # noqa: S307
        except Exception as e:
            return f"Calculation error: {e}"
    if action == "lookup":
        key = action_input.strip().lower()
        for fact_key, fact_val in _MATH_FACTS.items():
            if fact_key in key or key in fact_key:
                return fact_val
        return "No specific formula found. Use first-principles reasoning."
    if action == "verify":
        return f"Verification step logged: {action_input[:100]}"
    if action == "conclude":
        return "[Conclusion recorded]"
    return f"Unknown action '{action}'. Use: calculate, lookup, verify, or conclude."


async def react_reasoning(client: GroqClient, problem: str, max_steps: int = 8) -> str:
    """Run a ReAct reasoning loop."""
    messages: list[Message] = [
        Message(role="system", content=_REACT_SYSTEM),
        Message(role="user", content=f"Problem: {problem}"),
    ]
    trace: list[str] = []

    for step in range(max_steps):
        response = await client.complete(messages, temperature=0.2, max_tokens=200)
        agent_output = response.content.strip()
        messages.append(Message(role="assistant", content=agent_output))
        trace.append(f"[Step {step+1}]\n{agent_output}")

        # Check for conclusion
        if "final answer:" in agent_output.lower():
            break

        # Parse and execute action
        action_match = re.search(r"Action:\s*(.+)", agent_output, re.IGNORECASE)
        input_match  = re.search(r"Action Input:\s*(.+)", agent_output, re.IGNORECASE)

        if action_match and input_match:
            action      = action_match.group(1).strip()
            action_input= input_match.group(1).strip()
            observation = _react_execute(action, action_input)
            obs_message = f"Observation: {observation}"
            messages.append(Message(role="user", content=obs_message))
            trace.append(obs_message)

            if action.lower() == "conclude":
                break

    return "\n".join(trace)


# ---------------------------------------------------------------------------
# 4. Self-Consistency
# ---------------------------------------------------------------------------

_SC_SYSTEM = """\
Solve the problem carefully. Show your full reasoning, then state
your final numerical/factual answer on the last line as:
Answer: [value]
"""

_SC_AGGREGATOR_SYSTEM = """\
You are given multiple independent solutions to the same problem.
Identify the most common final answer (majority vote).
Explain any disagreements.
Output:
Majority Answer: [answer]
Confidence: [high/medium/low]
Reasoning: [brief explanation of why this is correct]
"""


async def self_consistency(
    client: GroqClient,
    problem: str,
    samples: int = 3,
) -> str:
    # Generate N independent solutions at higher temperature
    sample_tasks = [
        client.complete_text(
            problem,
            system=_SC_SYSTEM,
            temperature=0.8,   # diversity via higher temperature
            max_tokens=400,
        )
        for _ in range(samples)
    ]
    solutions = await asyncio.gather(*sample_tasks)

    # Aggregate
    combined = "\n\n---\n\n".join(f"Solution {i+1}:\n{s}" for i, s in enumerate(solutions))
    aggregated = await client.complete_text(
        f"Problem: {problem}\n\nSampled solutions:\n{combined}",
        system=_SC_AGGREGATOR_SYSTEM,
        temperature=0.0,
        max_tokens=300,
    )
    return f"[{samples} independent samples]\n\n{aggregated}"


# ---------------------------------------------------------------------------
# Comparison helper
# ---------------------------------------------------------------------------


@dataclass
class TechniqueResult:
    name: str
    output: str
    elapsed_s: float


@dataclass
class ReasoningResult:
    problem: str
    techniques: list[TechniqueResult] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Pattern
# ---------------------------------------------------------------------------


class ReasoningTechniquesPattern(BasePattern):
    """
    Demonstrates four advanced reasoning strategies on the same problem.

    CoT, ToT, ReAct, and Self-Consistency are applied in parallel where
    possible, then results are presented side-by-side.
    """

    name = "17 · Reasoning Techniques"

    async def _timed(self, name: str, coro: Any) -> TechniqueResult:
        import time
        start = time.perf_counter()
        output = await coro
        return TechniqueResult(name=name, output=output, elapsed_s=round(time.perf_counter() - start, 2))

    async def run(self, problem: str = DEFAULT_PROBLEM) -> ReasoningResult:  # type: ignore[override]
        self.print_header()
        print(f"Problem: {problem}\n")

        result = ReasoningResult(problem=problem)

        # Run all four techniques (CoT and SC in parallel; ToT and ReAct sequential for clarity)
        cot_result, sc_result = await asyncio.gather(
            self._timed("Chain-of-Thought (CoT)", chain_of_thought(self.client, problem)),
            self._timed("Self-Consistency (SC)", self_consistency(self.client, problem, samples=3)),
        )
        tot_result  = await self._timed("Tree-of-Thought (ToT)", tree_of_thought(self.client, problem, branches=3))
        react_result= await self._timed("ReAct (Reason+Act)",    react_reasoning(self.client, problem))

        for tr in [cot_result, tot_result, react_result, sc_result]:
            result.techniques.append(tr)
            self.print_step(f"Technique › {tr.name}  ({tr.elapsed_s}s)", tr.output)

        # Summary comparison
        comparison = await self.client.complete_text(
            "\n\n".join(
                f"[{t.name}]\n{t.output[:300]}…" for t in result.techniques
            ),
            system=(
                "Compare these four reasoning technique outputs for the same problem. "
                "Which gives the clearest explanation? Which is most reliable? "
                "Summarise in 3 bullet points."
            ),
            max_tokens=300,
        )
        self.print_step("Cross-Technique Comparison", comparison)

        self.print_result(
            " | ".join(f"{t.name}: {t.elapsed_s}s" for t in result.techniques)
        )
        return result
