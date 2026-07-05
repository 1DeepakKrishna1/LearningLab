"""
main.py — Agentic AI Design Patterns with LangGraph + Groq
===========================================================
Entry point for running one or all of the 21 agentic AI design patterns.

Usage:
    # Run all patterns
    python main.py

    # Run specific patterns
    python main.py --patterns 1 4 7

    # Run a single pattern with a custom task
    python main.py --patterns 1 --task "Write a blog post about edge computing"

    # Verbose: print full output of each pattern
    python main.py --verbose

    # List available patterns
    python main.py --list
"""
from __future__ import annotations

import argparse
import sys
import textwrap
import time
from typing import List, Optional

# Ensure stdout can handle any Unicode characters (important on Windows terminals)
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from dotenv import load_dotenv

load_dotenv()

from core.llm import GroqLLMClient
from core.base import PatternResult
from patterns import ALL_PATTERNS

# ------------------------------------------------------------------ Demo inputs
# Each tuple: (PatternClass, demo_input)
DEMO_INPUTS = {
    1:  "Write a technical blog post about quantum computing and its real-world applications",
    2:  [
            "How do I fix a segmentation fault in C++?",
            "Write a short poem about the ocean at night",
            "A farmer has 20 animals — some chickens, some rabbits. Total legs = 56. How many of each?",
            "What is the capital of Australia?",
        ],
    3:  "AI-powered personalised fitness coach app that adapts workouts in real time",
    4:  "Write a persuasive argument for why every developer should learn Rust",
    5:  "Plan a 5-night trip to Tokyo: convert $3000 USD to JPY, estimate hotel costs, and find out what day next Monday is",
    6:  "Design and build a Python CLI tool that monitors system CPU and memory usage and sends email alerts",
    7:  "Create a comprehensive market research report on the rise of AI coding assistants",
    8:  "Career advice and skill development",
    9:  "General knowledge trivia",
    10: "I can't access my account after the recent platform update",
    11: "Improve code quality of a Python calculator function",
    12: "Run the quarterly sales data pipeline: fetch → transform → analyse → report",
    13: "Schedule a Q2 planning meeting with the engineering team for next Monday at 10 AM",
    14: [
            "Who created Python and when?",
            "What frameworks are available for Python web development?",
            "How does Python handle asynchronous programming?",
        ],
    15: "Advances in large language model efficiency and quantisation techniques",
    16: "Answer a variety of ML questions within a limited token budget",
    17: "A train leaves City A at 60 km/h. Another leaves City B (300 km away) towards A at 90 km/h. Where do they meet?",
    18: "Process a mixed set of user requests including safe and unsafe inputs",
    19: "Evaluate AI-generated responses across multiple question types",
    20: "Prioritise and execute 8 pending work tasks with varying urgency and importance",
    21: "Discover innovative product ideas combining AI with sustainability",
}


# ------------------------------------------------------------------ Runner

def run_patterns(
    pattern_numbers: Optional[List[int]] = None,
    custom_task: Optional[str] = None,
    verbose: bool = False,
) -> List[PatternResult]:
    """Instantiate and run the requested patterns, returning all PatternResult objects."""
    print("\n" + "=" * 70)
    print("  Agentic AI Design Patterns -- LangGraph + Groq")
    print("=" * 70)

    # Initialise shared LLM client
    try:
        llm = GroqLLMClient()
        print(f"  LLM client initialised (Groq)")
    except EnvironmentError as e:
        print(f"\n[ERROR] Configuration error: {e}")
        print("   Copy .env.example to .env and add your GROQ_API_KEY.\n")
        sys.exit(1)

    # Filter patterns to run
    targets = ALL_PATTERNS
    if pattern_numbers:
        targets = [p for p in ALL_PATTERNS if p.PATTERN_NUMBER in pattern_numbers]
        if not targets:
            print(f"\n[WARN] No patterns found for numbers: {pattern_numbers}")
            return []

    results: List[PatternResult] = []
    total_start = time.perf_counter()

    for PatternClass in targets:
        num = PatternClass.PATTERN_NUMBER
        name = PatternClass.PATTERN_NAME
        demo_input = custom_task if custom_task else DEMO_INPUTS.get(num, f"Demo task for pattern {num}")

        sep = "-" * 70
        print(f"\n{sep}")
        print(f"  Pattern {num:02d} / 21 -- {name}")
        print(sep)
        if verbose:
            input_preview = str(demo_input)[:120] + ("..." if len(str(demo_input)) > 120 else "")
            print(f"  Input: {input_preview}")

        pattern = PatternClass(llm)
        result = pattern.run(demo_input)
        results.append(result)

        status = "[OK]" if result.success else "[FAIL]"
        print(f"  {status}  {result.execution_time_ms:.0f} ms  |  Steps: {len(result.steps)}")

        if result.success:
            if verbose:
                output_str = str(result.output_data)
                wrapped = textwrap.fill(output_str[:600], width=68, initial_indent="  ", subsequent_indent="  ")
                print(f"\n  OUTPUT:\n{wrapped}")
                if len(output_str) > 600:
                    print("  [...truncated]")
            else:
                output_preview = str(result.output_data)[:200].replace("\n", " ")
                print(f"  Output: {output_preview}…")
        else:
            print(f"  Error: {str(result.error)[:200]}")

    # ---------------------------------------------------------------- Summary
    total_elapsed = (time.perf_counter() - total_start) * 1000
    success_count = sum(1 for r in results if r.success)
    fail_count = len(results) - success_count

    print(f"\n{'=' * 70}")
    print(f"  Results: {success_count}/{len(results)} patterns succeeded")
    if fail_count:
        print(f"  Failed:  {fail_count}")
        for r in results:
            if not r.success:
                print(f"    - Pattern {r.pattern_number:02d} ({r.pattern_name}): {str(r.error)[:80]}")
    print(f"  Total time: {total_elapsed / 1000:.1f}s")
    print(f"{'=' * 70}\n")

    return results


def list_patterns() -> None:
    print("\nAvailable patterns:\n")
    for PatternClass in ALL_PATTERNS:
        print(f"  {PatternClass.PATTERN_NUMBER:02d}  {PatternClass.PATTERN_NAME}")
        if PatternClass.DESCRIPTION:
            desc = textwrap.fill(PatternClass.DESCRIPTION, width=64, initial_indent="      ", subsequent_indent="      ")
            print(desc)
    print()


# ------------------------------------------------------------------ CLI

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run Agentic AI Design Patterns with LangGraph + Groq",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""\
            Examples:
              python main.py                          # run all 21 patterns
              python main.py --patterns 1 4 7         # run specific patterns
              python main.py --patterns 5 --verbose   # verbose output
              python main.py --list                   # list all patterns
        """),
    )
    parser.add_argument(
        "--patterns", "-p",
        nargs="*",
        type=int,
        metavar="N",
        help="Pattern numbers to run (default: all)",
    )
    parser.add_argument(
        "--task", "-t",
        type=str,
        default=None,
        help="Custom task string (overrides default demo input for each pattern)",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Print full output for each pattern",
    )
    parser.add_argument(
        "--list", "-l",
        action="store_true",
        help="List all available patterns and exit",
    )

    args = parser.parse_args()

    if args.list:
        list_patterns()
        return

    run_patterns(
        pattern_numbers=args.patterns,
        custom_task=args.task,
        verbose=args.verbose,
    )


if __name__ == "__main__":
    main()
