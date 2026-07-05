"""
Thread-safe TTL in-memory query cache backed by asyncio.Lock.

Cache key: SHA-256( dataset_id + ":" + sql )
Entries expire after `ttl_seconds` (default: settings.cache_ttl_seconds).
"""
from __future__ import annotations

import asyncio
import hashlib
import time
from typing import Any

from loguru import logger

from app.config import get_settings

settings = get_settings()


class TTLCache:
    """Simple async-safe TTL cache."""

    def __init__(self, ttl_seconds: int | None = None) -> None:
        self._ttl = ttl_seconds if ttl_seconds is not None else settings.cache_ttl_seconds
        self._store: dict[str, tuple[Any, float]] = {}  # key → (value, expiry_ts)
        self._lock = asyncio.Lock()

    @staticmethod
    def make_key(dataset_id: str, sql: str) -> str:
        raw = f"{dataset_id}:{sql}"
        return hashlib.sha256(raw.encode()).hexdigest()

    async def get(self, key: str) -> Any | None:
        async with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return None
            value, expiry = entry
            if time.monotonic() > expiry:
                del self._store[key]
                logger.debug("cache_expired", key=key[:16])
                return None
            logger.debug("cache_hit", key=key[:16])
            return value

    async def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        ttl = ttl if ttl is not None else self._ttl
        async with self._lock:
            self._store[key] = (value, time.monotonic() + ttl)
            logger.debug("cache_set", key=key[:16], ttl=ttl)

    async def delete(self, key: str) -> None:
        async with self._lock:
            self._store.pop(key, None)

    async def clear_dataset(self, dataset_id: str) -> int:
        """Remove all entries whose key starts with dataset_id prefix (best-effort)."""
        prefix = hashlib.sha256(f"{dataset_id}:".encode()).hexdigest()[:8]
        async with self._lock:
            before = len(self._store)
            self._store = {
                k: v
                for k, v in self._store.items()
                if not k.startswith(prefix)
            }
            removed = before - len(self._store)
        logger.info("cache_cleared_dataset", dataset_id=dataset_id, removed=removed)
        return removed

    async def purge_expired(self) -> int:
        """Remove all expired entries. Call periodically if needed."""
        now = time.monotonic()
        async with self._lock:
            before = len(self._store)
            self._store = {k: v for k, v in self._store.items() if v[1] > now}
            removed = before - len(self._store)
        logger.debug("cache_purged_expired", removed=removed)
        return removed

    @property
    def size(self) -> int:
        return len(self._store)


# Singleton shared across the application
query_cache = TTLCache()
