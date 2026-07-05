"""
Agentic AI Design Patterns – Demo Runner
==========================================
Demonstrates all 21 agentic patterns with a shared Groq client.

Usage:
    python main.py                     # run all 21 patterns
    python main.py --pattern 17        # run only pattern 17
    python main.py --from 15 --to 21   # run new patterns only
    python main.py --list              # list all patterns
    python main.py --verbose           # enable debug logging

Setup:
    1. pip install -r requirements.txt
    2. Copy .env.example to .env and add your GROQ_API_KEY
       OR: export GROQ_API_KEY=your_key_here
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
import time
from typing import Any

# Ensure UTF-8 output on Windows (cp1252 cannot encode box-drawing characters)
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from llm_client import GroqClient, LLMError, LLMConfigError
from patterns import (
    # 1–7: Core
    PromptChainingPattern,
    RoutingPattern,
    ParallelizationPattern,
    ReflectionPattern,
    ToolUsePattern,
    PlanningPattern,
    MultiAgentPattern,
    # 8–14: Extended
    MemoryManagementPattern,
    LearningAdaptationPattern,
    ModelContextProtocolPattern,
    GoalMonitoringPattern,
    ExceptionRecoveryPattern,
    HumanInTheLoopPattern,
    KnowledgeRetrievalPattern,
    # 15–21: Advanced
    InterAgentCommunicationPattern,
    ResourceOptimizationPattern,
    ReasoningTechniquesPattern,
    GuardrailsSafetyPattern,
    EvaluationMonitoringPattern,
    PrioritizationPattern,
    ExplorationDiscoveryPattern,
)

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Pattern registry  — (PatternClass, run_kwargs)
# ---------------------------------------------------------------------------

PATTERN_REGISTRY: list[tuple[type, dict[str, Any]]] = [
    # ── 1–7: Core patterns ───────────────────────────────────────────
    (PromptChainingPattern,   {"topic": "The impact of AI on software engineering"}),
    (RoutingPattern,          {"query": "Explain how transformer neural networks work in simple terms"}),
    (ParallelizationPattern,  {"topic": "Generative AI replacing creative professionals"}),
    (ReflectionPattern,       {
        "task": "Write a Python function that merges two sorted lists into a single sorted list",
        "iterations": 2,
    }),
    (ToolUsePattern,          {
        "query": (
            "What is 15 squared plus the square root of 2025? "
            "Convert the answer from km to miles. What is today's date?"
        )
    }),
    (PlanningPattern,         {"goal": "Create a go-to-market strategy for a new AI-powered code review SaaS product"}),
    (MultiAgentPattern,       {"topic": "The future of AI-assisted software development by 2030"}),

    # ── 8–14: Extended patterns ──────────────────────────────────────
    (MemoryManagementPattern, {
        "turns": [
            "Hi! I'm Alex. I'm a Python developer and I love hiking.",
            "What programming language do I use and what's my hobby?",
            "I'm also learning Rust and planning a trip to Patagonia next year.",
            "Summarise everything you know about me.",
        ]
    }),
    (LearningAdaptationPattern, {
        "prompt": "Explain the concept of recursion in programming.",
        "feedback_rounds": [
            {"rating": 2, "comment": "Too verbose. Use bullet points with a short code example."},
            {"rating": 4, "comment": "Better! Always include time/space complexity for algorithms."},
        ],
    }),
    (ModelContextProtocolPattern, {"query": "What products does our company offer and what is today's date?"}),
    (GoalMonitoringPattern,   {
        "goal_title": "Launch an open-source Python library for LLM prompt management",
        "goal_description": (
            "Build and release a well-documented, production-ready Python library that helps "
            "developers manage, version, and test LLM prompts across multiple providers."
        ),
    }),
    (ExceptionRecoveryPattern, {"prompt": "Explain the CAP theorem in distributed systems."}),
    (HumanInTheLoopPattern,   {"topic": "Best practices for securing REST APIs", "interactive": False}),
    (KnowledgeRetrievalPattern, {
        "questions": [
            "What are the main improvements in TLS 1.3 over TLS 1.2?",
            "How should I implement authentication for a machine-to-machine API?",
            "What is the primary defence against SQL injection attacks?",
        ]
    }),

    # ── 15–21: Advanced patterns ─────────────────────────────────────
    (InterAgentCommunicationPattern, {
        "topic": "Zero-trust security architecture for cloud-native applications",
    }),
    (ResourceOptimizationPattern, {"token_limit": 5_000, "call_limit": 8}),
    (ReasoningTechniquesPattern,  {
        "problem": (
            "A train travels from City A to City B at 60 km/h and returns at 40 km/h. "
            "What is the average speed for the entire round trip? "
            "Why is the naive average of (60+40)/2 = 50 km/h incorrect?"
        )
    }),
    (GuardrailsSafetyPattern,     {}),
    (EvaluationMonitoringPattern, {}),
    (PrioritizationPattern,       {"use_llm_triage": True}),
    (ExplorationDiscoveryPattern, {
        "seed": "Zero-Knowledge Proofs",
        "strategy": "bfs",
        "max_depth": 2,
        "max_nodes": 10,
    }),
]


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------


async def run_pattern(client: GroqClient, pattern_cls: type, kwargs: dict[str, Any]) -> None:
    pattern = pattern_cls(client)
    start = time.perf_counter()
    try:
        await pattern.run(**kwargs)
    except LLMError as exc:
        print(f"\n[ERROR] {pattern.name} failed: {exc}")
        logger.error("Pattern %s failed: %s", pattern_cls.__name__, exc)
    elapsed = round(time.perf_counter() - start, 2)
    print(f"\n[Timing] {pattern.name} completed in {elapsed}s")


async def run_all(client: GroqClient, indices: list[int]) -> None:
    total = len(indices)
    for pos, idx in enumerate(indices, start=1):
        pattern_cls, kwargs = PATTERN_REGISTRY[idx]
        print(f"\n\n{'#' * 70}")
        print(f"#  Pattern {idx + 1}/{len(PATTERN_REGISTRY)}  [{pos}/{total} selected]")
        print(f"{'#' * 70}")
        await run_pattern(client, pattern_cls, kwargs)
        if pos < total:
            await asyncio.sleep(1)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    n = len(PATTERN_REGISTRY)
    parser = argparse.ArgumentParser(
        description=f"Agentic AI Design Patterns Demo (Groq) — {n} patterns",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--pattern",             type=int, metavar=f"[1-{n}]", help="Run only this pattern (1-indexed).")
    parser.add_argument("--from", dest="from_p", type=int, metavar=f"[1-{n}]", help="Start of range (inclusive).")
    parser.add_argument("--to",   dest="to_p",   type=int, metavar=f"[1-{n}]", help="End of range (inclusive).")
    parser.add_argument("--list",    action="store_true", help="List all patterns and exit.")
    parser.add_argument("--verbose", action="store_true", help="Enable DEBUG logging.")
    return parser


def list_patterns() -> None:
    groups = [
        ("Core Patterns     (1–7)",  range(1,  8)),
        ("Extended Patterns (8–14)", range(8,  15)),
        ("Advanced Patterns (15–21)",range(15, 22)),
    ]
    print()
    for group_name, rng in groups:
        print(f"  ── {group_name} {'─' * (36 - len(group_name))}")
        for i in rng:
            cls = PATTERN_REGISTRY[i - 1][0]
            print(f"    {i:>2}.  {cls.name}")
    print()


async def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    n = len(PATTERN_REGISTRY)

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    if args.list:
        list_patterns()
        return 0

    try:
        client = GroqClient()
    except LLMConfigError as exc:
        print(f"\n[CONFIG ERROR] {exc}", file=sys.stderr)
        return 1

    if args.pattern:
        indices = [args.pattern - 1]
    elif args.from_p or args.to_p:
        start = (args.from_p or 1) - 1
        end   = (args.to_p   or n) - 1
        indices = list(range(start, end + 1))
    else:
        indices = list(range(n))

    indices = [i for i in indices if 0 <= i < n]

    print("\n" + "=" * 70)
    print("  Agentic AI Design Patterns — 21 Patterns — powered by Groq")
    print("=" * 70)
    print(f"  Model         : {client.model}")
    print(f"  Total patterns: {n}")
    print(f"  Running       : {len(indices)} pattern(s)")
    print("=" * 70)

    t0 = time.perf_counter()
    await run_all(client, indices)
    elapsed = round(time.perf_counter() - t0, 2)

    print(f"\n\n{'=' * 70}")
    print(f"  All {len(indices)} pattern(s) completed in {elapsed}s")
    print(f"{'=' * 70}\n")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
