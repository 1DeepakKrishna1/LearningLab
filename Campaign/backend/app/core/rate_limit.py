"""Simple in-memory sliding-window rate limiter.

Suitable for a single-process self-hosted deployment. For multi-worker setups
swap the backing store for Redis (the public ``hit`` API stays the same).
"""
from __future__ import annotations

import threading
import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request, status

from app.core.config import settings


class SlidingWindowLimiter:
    def __init__(self) -> None:
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def hit(self, key: str, limit: int, window: int) -> bool:
        """Record a hit. Return ``True`` if allowed, ``False`` if over the limit."""
        now = time.monotonic()
        with self._lock:
            q = self._hits[key]
            cutoff = now - window
            while q and q[0] < cutoff:
                q.popleft()
            if len(q) >= limit:
                return False
            q.append(now)
            return True


limiter = SlidingWindowLimiter()


def _client_ip(request: Request) -> str:
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def rate_limit_dependency(request: Request) -> None:
    """Global per-IP rate limit dependency."""
    key = f"global:{_client_ip(request)}"
    if not limiter.hit(key, settings.RATE_LIMIT_REQUESTS, settings.RATE_LIMIT_WINDOW_SECONDS):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Please slow down.",
        )


def login_rate_limit(request: Request) -> None:
    """Stricter limit for auth endpoints to slow brute-force attempts."""
    key = f"login:{_client_ip(request)}"
    if not limiter.hit(
        key, settings.LOGIN_RATE_LIMIT_REQUESTS, settings.LOGIN_RATE_LIMIT_WINDOW_SECONDS
    ):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many login attempts. Try again later.",
        )
