"""
Background task: listen for Redis keyspace expiry events and keep the
in-memory vector index in sync.

Two-layer stale-index defence
──────────────────────────────
Layer 1 (this file — proactive):
    Subscribe to ``__keyevent@{db}__:expired``.  Fires within milliseconds
    of a key expiry.  Removes the entry from the index and cleans up the
    membership Set.

Layer 2 (cache.py — reactive):
    Before returning a candidate hit, ``cache.py`` validates the entry still
    exists in Redis.  If the listener was temporarily down and the entry
    expired undetected, the stale id is removed from the index at that point.
"""

from __future__ import annotations

import asyncio
import logging

from semantic_cache.index.vector_index import VectorIndex
from semantic_cache.store.redis_store import RedisStore

logger = logging.getLogger(__name__)


class ExpiryListener:
    """
    Wraps the pubsub loop as a managed asyncio Task.

    Usage::

        listener = ExpiryListener(store, index)
        task = asyncio.create_task(listener.run(), name="semcache-expiry-listener")
        # …
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)
    """

    def __init__(self, store: RedisStore, index: VectorIndex) -> None:
        self._store = store
        self._index = index

    async def run(self, db_index: int = 0) -> None:
        """
        Entry point for ``asyncio.create_task``.  Runs until cancelled.
        Reconnects automatically after transient Redis errors.
        """
        await self._store.subscribe_expiry_events(
            db_index=db_index,
            callback=self._handle_expiry,
        )

    async def _handle_expiry(self, entry_id: str) -> None:
        """
        Called by ``RedisStore.subscribe_expiry_events`` for every matched
        expiry event.

        Steps:
        1. Remove the vector from the in-memory index (O(N) scan, rare path).
        2. SREM the entry_id from the Redis membership Set (the Hash is
           already gone — Redis expired it).
        """
        removed = await self._index.remove(entry_id)
        await self._store.delete_entry(entry_id)  # idempotent: only SREM matters
        if removed:
            logger.debug("ExpiryListener: evicted entry %s from index.", entry_id)
        else:
            logger.debug(
                "ExpiryListener: entry %s expired in Redis but was not in index "
                "(may have been removed earlier).",
                entry_id,
            )
