"""
Pattern 12 – Exception Handling and Recovery
=============================================
Production agentic systems must handle failures gracefully.  This
pattern demonstrates a layered recovery strategy:

  Layer 1 – Retry with exponential back-off
             For transient errors (rate limits, timeouts, flaky APIs).

  Layer 2 – Prompt simplification
             If the model consistently rejects a complex request,
             strip it down to its essential question.

  Layer 3 – Model fallback
             Switch to a lighter/different model when the primary
             model is unavailable or over-loaded.

  Layer 4 – Graceful degradation
             Return a partial/cached result rather than failing hard,
             logging a structured error report for observability.

The demo intentionally injects different failure modes and shows
how the recovery chain handles each one.
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Coroutine, Optional, TypeVar

from llm_client import GroqClient, LLMError, LLMRateLimitError, LLMTimeoutError, FAST_MODEL
from patterns.base import BasePattern

logger = logging.getLogger(__name__)

T = TypeVar("T")


# ---------------------------------------------------------------------------
# Error classification
# ---------------------------------------------------------------------------


class ErrorCategory(str, Enum):
    RATE_LIMIT = "rate_limit"
    TIMEOUT = "timeout"
    MODEL_ERROR = "model_error"
    VALIDATION = "validation"
    UNKNOWN = "unknown"


def classify_error(exc: Exception) -> ErrorCategory:
    if isinstance(exc, LLMRateLimitError):
        return ErrorCategory.RATE_LIMIT
    if isinstance(exc, LLMTimeoutError):
        return ErrorCategory.TIMEOUT
    if isinstance(exc, LLMError):
        return ErrorCategory.MODEL_ERROR
    return ErrorCategory.UNKNOWN


# ---------------------------------------------------------------------------
# Retry decorator with exponential back-off
# ---------------------------------------------------------------------------


@dataclass
class RetryConfig:
    max_attempts: int = 3
    base_delay_s: float = 1.0
    backoff_factor: float = 2.0
    retryable_categories: frozenset[ErrorCategory] = field(
        default_factory=lambda: frozenset(
            {ErrorCategory.RATE_LIMIT, ErrorCategory.TIMEOUT, ErrorCategory.UNKNOWN}
        )
    )


async def with_retry(
    fn: Callable[[], Coroutine[Any, Any, T]],
    config: RetryConfig = RetryConfig(),
    on_retry: Optional[Callable[[int, Exception, float], None]] = None,
) -> T:
    """
    Execute ``fn`` with exponential back-off retry.

    Args:
        fn:        Async callable to attempt.
        config:    Retry parameters.
        on_retry:  Optional callback(attempt, exc, delay) for observability.

    Returns:
        The result of ``fn`` on success.

    Raises:
        The last exception if all attempts are exhausted.
    """
    last_exc: Exception = RuntimeError("No attempts made")
    for attempt in range(1, config.max_attempts + 1):
        try:
            return await fn()
        except Exception as exc:
            last_exc = exc
            category = classify_error(exc)
            if category not in config.retryable_categories or attempt == config.max_attempts:
                raise
            delay = config.base_delay_s * (config.backoff_factor ** (attempt - 1))
            if on_retry:
                on_retry(attempt, exc, delay)
            logger.warning(
                "Attempt %d/%d failed (%s). Retrying in %.1fs…",
                attempt, config.max_attempts, category.value, delay,
            )
            await asyncio.sleep(delay)
    raise last_exc  # unreachable but satisfies type checker


# ---------------------------------------------------------------------------
# Recovery strategies
# ---------------------------------------------------------------------------


@dataclass
class RecoveryAttempt:
    strategy: str
    succeeded: bool = False
    result: str = ""
    error: str = ""


@dataclass
class RecoveryResult:
    prompt: str
    attempts: list[RecoveryAttempt] = field(default_factory=list)
    final_result: str = ""
    recovered: bool = False


class RecoveryOrchestrator:
    """
    Applies a layered recovery chain to a failing LLM request.

    Strategies are tried in order until one succeeds or all fail.
    """

    def __init__(self, client: GroqClient) -> None:
        self.client = client

    async def execute_with_recovery(
        self,
        prompt: str,
        system: str = "You are a helpful assistant.",
        *,
        inject_failure: Optional[str] = None,
    ) -> RecoveryResult:
        """
        Attempt ``prompt`` with the full recovery chain.

        Args:
            prompt:         The user prompt to complete.
            system:         System instruction.
            inject_failure: For demo purposes – simulate a failure type.
                            One of: "rate_limit", "timeout", "model_error".
        """
        result = RecoveryResult(prompt=prompt)

        # ── Strategy 1: Retry with back-off ───────────────────────────
        attempt_log = RecoveryAttempt(strategy="retry_with_backoff")
        try:
            call_count = 0

            async def attempt() -> str:
                nonlocal call_count
                call_count += 1
                # Inject failure for first 2 attempts in demo
                if inject_failure and call_count <= 2:
                    if inject_failure == "rate_limit":
                        raise LLMRateLimitError("Simulated: 429 rate limit exceeded")
                    if inject_failure == "timeout":
                        raise LLMTimeoutError("Simulated: request timed out")
                return await self.client.complete_text(
                    prompt, system=system, max_tokens=400
                )

            def on_retry(attempt_num: int, exc: Exception, delay: float) -> None:
                logger.info("  Retry %d after %.1fs (%s)", attempt_num, delay, exc)

            text = await with_retry(attempt, RetryConfig(max_attempts=3, base_delay_s=0.5), on_retry)
            attempt_log.succeeded = True
            attempt_log.result = text
            result.attempts.append(attempt_log)
            result.final_result = text
            result.recovered = True
            return result

        except Exception as exc:
            attempt_log.succeeded = False
            attempt_log.error = str(exc)
            result.attempts.append(attempt_log)
            logger.warning("Strategy 1 exhausted: %s", exc)

        # ── Strategy 2: Prompt simplification ─────────────────────────
        attempt_log2 = RecoveryAttempt(strategy="prompt_simplification")
        try:
            # Distill the prompt to its core question
            simple_prompt = await self.client.complete_text(
                f"Reduce this to one simple, direct question (max 15 words): {prompt}",
                system="Return only the simplified question.",
                model=FAST_MODEL,
                max_tokens=50,
            )
            text = await self.client.complete_text(
                simple_prompt, system=system, max_tokens=300
            )
            attempt_log2.succeeded = True
            attempt_log2.result = f"[Simplified prompt: {simple_prompt}]\n\n{text}"
            result.attempts.append(attempt_log2)
            result.final_result = attempt_log2.result
            result.recovered = True
            return result

        except Exception as exc:
            attempt_log2.succeeded = False
            attempt_log2.error = str(exc)
            result.attempts.append(attempt_log2)
            logger.warning("Strategy 2 failed: %s", exc)

        # ── Strategy 3: Model fallback ─────────────────────────────────
        attempt_log3 = RecoveryAttempt(strategy="model_fallback")
        try:
            text = await self.client.complete_text(
                prompt, system=system, model=FAST_MODEL, max_tokens=300
            )
            attempt_log3.succeeded = True
            attempt_log3.result = f"[Fallback model: {FAST_MODEL}]\n\n{text}"
            result.attempts.append(attempt_log3)
            result.final_result = attempt_log3.result
            result.recovered = True
            return result

        except Exception as exc:
            attempt_log3.succeeded = False
            attempt_log3.error = str(exc)
            result.attempts.append(attempt_log3)
            logger.warning("Strategy 3 failed: %s", exc)

        # ── Strategy 4: Graceful degradation ──────────────────────────
        degraded_msg = (
            f"[DEGRADED] Unable to process request after {len(result.attempts)} recovery attempts.\n"
            f"Original prompt: {prompt[:200]}…\n"
            f"Errors: " + " | ".join(
                f"{a.strategy}: {a.error}" for a in result.attempts if not a.succeeded
            )
        )
        result.attempts.append(
            RecoveryAttempt(strategy="graceful_degradation", succeeded=False, result=degraded_msg)
        )
        result.final_result = degraded_msg
        result.recovered = False
        return result


# ---------------------------------------------------------------------------
# Pattern
# ---------------------------------------------------------------------------


class ExceptionRecoveryPattern(BasePattern):
    """
    Demonstrates layered exception handling and recovery.

    Runs three scenarios:
      A) No failure         → succeeds on first attempt
      B) Rate-limit failure → recovered via retry back-off
      C) Persistent failure → recovered via prompt simplification
    """

    name = "12 · Exception Handling and Recovery"

    async def run(self, prompt: str = "Explain the CAP theorem in distributed systems.") -> dict[str, Any]:  # type: ignore[override]
        self.print_header()
        orchestrator = RecoveryOrchestrator(self.client)
        all_results: list[RecoveryResult] = []

        scenarios: list[tuple[str, Optional[str]]] = [
            ("Scenario A: Normal execution (no failure)",          None),
            ("Scenario B: Rate-limit failure → retry back-off",    "rate_limit"),
            ("Scenario C: Timeout failure → retry + model fallback", "timeout"),
        ]

        for label, inject in scenarios:
            self.print_step(label, f"Prompt: {prompt}")
            start = time.perf_counter()
            res = await orchestrator.execute_with_recovery(
                prompt,
                inject_failure=inject,
            )
            elapsed = round(time.perf_counter() - start, 2)

            for i, a in enumerate(res.attempts, 1):
                status = "✓" if a.succeeded else "✗"
                self.print_step(
                    f"  Attempt {i} › {a.strategy}  [{status}]",
                    (a.result[:300] + "…") if a.succeeded and len(a.result) > 300
                    else (a.error if not a.succeeded else a.result),
                )

            recovered_str = "RECOVERED" if res.recovered else "DEGRADED"
            print(f"\n  → {recovered_str} in {elapsed}s after {len(res.attempts)} attempt(s)")
            all_results.append(res)

        self.print_result(
            "\n".join(
                f"  {s[0]}: {'✓' if r.recovered else '✗'}"
                for s, r in zip(scenarios, all_results)
            )
        )

        return {
            "prompt": prompt,
            "scenarios": [
                {
                    "label": s[0],
                    "recovered": r.recovered,
                    "attempts": len(r.attempts),
                }
                for s, r in zip(scenarios, all_results)
            ],
        }
