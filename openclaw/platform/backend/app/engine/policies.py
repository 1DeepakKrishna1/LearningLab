"""Retry and timeout policies for node execution."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any, Awaitable, Callable

from ..logging_setup import get_logger

logger = get_logger("engine.policies")


@dataclass(frozen=True)
class RetryPolicy:
    max_retries: int = 0
    base_delay: float = 0.5
    max_delay: float = 10.0

    def delay_for(self, attempt: int) -> float:
        return min(self.base_delay * (2 ** (attempt - 1)), self.max_delay)


@dataclass(frozen=True)
class TimeoutPolicy:
    seconds: float | None = None


async def run_with_policies(
    coro_factory: Callable[[], Awaitable[Any]],
    retry: RetryPolicy,
    timeout: TimeoutPolicy,
    on_retry: Callable[[int, Exception], None] | None = None,
) -> Any:
    """Run ``coro_factory()`` under timeout + retry policies.

    ``coro_factory`` must produce a fresh awaitable on each attempt (so retries
    re-issue the work). Raises the last exception if all attempts fail.
    """
    attempt = 0
    last_exc: Exception | None = None
    while attempt <= retry.max_retries:
        attempt += 1
        try:
            if timeout.seconds:
                return await asyncio.wait_for(coro_factory(), timeout=timeout.seconds)
            return await coro_factory()
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
            if attempt > retry.max_retries:
                break
            if on_retry:
                on_retry(attempt, exc)
            delay = retry.delay_for(attempt)
            logger.warning("Attempt %d failed (%s); retrying in %.1fs", attempt, exc, delay)
            await asyncio.sleep(delay)
    assert last_exc is not None
    raise last_exc
