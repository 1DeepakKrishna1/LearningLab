"""Retry utilities using tenacity for robust production error handling."""

import functools
from typing import Any, Callable, Sequence, Type

from tenacity import (
    RetryError,
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
    wait_random_exponential,
)

from src.utils.logger import get_logger

logger = get_logger(__name__)


def retry_with_backoff(
    exceptions: Sequence[Type[Exception]] = (Exception,),
    max_attempts: int = 3,
    min_wait: float = 1.0,
    max_wait: float = 60.0,
    jitter: bool = True,
) -> Callable:
    """Decorator factory for retrying functions with exponential backoff.

    Uses random jitter by default to prevent thundering-herd on external APIs.
    """
    wait = (
        wait_random_exponential(min=min_wait, max=max_wait)
        if jitter
        else wait_exponential(min=min_wait, max=max_wait)
    )

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            retrier = retry(
                reraise=True,
                stop=stop_after_attempt(max_attempts),
                wait=wait,
                retry=retry_if_exception_type(tuple(exceptions)),
                before_sleep=before_sleep_log(logger, log_level=20),  # INFO
            )
            return retrier(func)(*args, **kwargs)

        return wrapper

    return decorator


def retry_api_call(max_attempts: int = 3) -> Callable:
    """Specialised retry for LLM/external API calls with rate-limit awareness."""
    import httpx

    return retry_with_backoff(
        exceptions=(Exception, httpx.HTTPError, ConnectionError, TimeoutError),
        max_attempts=max_attempts,
        min_wait=2.0,
        max_wait=120.0,
        jitter=True,
    )
