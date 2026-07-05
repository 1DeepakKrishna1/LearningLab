"""All Redis I/O: entries, membership index, TTL, and keyspace notifications."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator
from typing import Callable, Coroutine, Any

import redis.asyncio as aioredis
from redis.asyncio import Redis
from redis.exceptions import ResponseError

from semantic_cache.exceptions import CacheCorruptionError, RedisConnectionError
from semantic_cache.store.schemas import CacheEntry

logger = logging.getLogger(__name__)


class RedisStore:
    """
    Manages two Redis structures per cache entry:

        {prefix}:entry:{entry_id}  → Hash  (all CacheEntry fields, with TTL)
        {prefix}:index             → Set   (all known entry_ids, permanent)

    The Set acts as a directory for cold-start index rebuilds.  Because only
    the Hash keys carry a TTL, the Set may accumulate stale ids; ``prune_stale_ids``
    (called at startup) cleans those up.
    """

    def __init__(
        self,
        redis_url: str,
        key_prefix: str,
        client: Redis | None = None,
    ) -> None:
        self._url = redis_url
        self._prefix = key_prefix
        self._client: Redis | None = client  # accept a pre-built client (e.g. fakeredis)

    # ── Lifecycle ──────────────────────────────────────────────────────

    async def connect(self) -> None:
        if self._client is None:
            self._client = aioredis.from_url(
                self._url,
                decode_responses=False,
                socket_keepalive=True,
                health_check_interval=30,
            )
        try:
            await self._client.ping()
        except Exception as exc:
            raise RedisConnectionError(f"Cannot connect to Redis at {self._url}: {exc}") from exc
        logger.info("RedisStore connected to %s", self._url)

    async def close(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None

    @property
    def client(self) -> Redis:
        if self._client is None:
            raise RedisConnectionError("RedisStore.connect() has not been called.")
        return self._client

    # ── Keyspace notifications ──────────────────────────────────────────

    async def enable_keyspace_notifications(self) -> None:
        """
        Enable keyspace expired-event notifications.
        Silently skips if CONFIG SET is not permitted (e.g. managed Redis).
        """
        try:
            await self.client.config_set("notify-keyspace-events", "Kx")
            logger.info("Keyspace notifications enabled (Kx).")
        except ResponseError as exc:
            logger.warning(
                "Could not enable keyspace notifications (%s). "
                "Stale-index cleanup will rely on validation-on-read only.",
                exc,
            )

    async def subscribe_expiry_events(
        self,
        db_index: int,
        callback: Callable[[str], Coroutine[Any, Any, None]],
    ) -> None:
        """
        Long-running coroutine: subscribe to expiry keyspace events and
        invoke ``callback(entry_id)`` for every matching key expiry.
        Reconnects automatically on transient errors.
        """
        channel = f"__keyevent@{db_index}__:expired"
        entry_prefix = f"{self._prefix}:entry:"

        while True:
            pubsub = self.client.pubsub()
            try:
                await pubsub.subscribe(channel)
                logger.info("ExpiryListener subscribed to %s", channel)
                async for message in pubsub.listen():
                    if message["type"] != "message":
                        continue
                    raw_key: bytes = message["data"]
                    key = raw_key.decode() if isinstance(raw_key, bytes) else raw_key
                    if key.startswith(entry_prefix):
                        entry_id = key[len(entry_prefix):]
                        await callback(entry_id)
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.error("ExpiryListener error (%s), reconnecting in 2 s…", exc)
                await asyncio.sleep(2)
            finally:
                try:
                    await pubsub.unsubscribe(channel)
                    await pubsub.aclose()
                except Exception:
                    pass

    # ── CRUD ───────────────────────────────────────────────────────────

    def _hash_key(self, entry_id: str) -> str:
        return f"{self._prefix}:entry:{entry_id}"

    def _index_key(self) -> str:
        return f"{self._prefix}:index"

    async def save_entry(self, entry: CacheEntry) -> None:
        """
        Persist a CacheEntry.  Uses a pipeline for near-atomicity:
        HSET the hash → SADD to index Set → EXPIRE the hash (not the Set).
        """
        hash_key = self._hash_key(entry.entry_id)
        pipe = self.client.pipeline(transaction=True)
        pipe.hmset(hash_key, entry.to_redis_hash())
        pipe.sadd(self._index_key(), entry.entry_id)
        if entry.ttl > 0:
            pipe.expire(hash_key, entry.ttl)
        await pipe.execute()
        logger.debug("Saved entry %s (ttl=%ds)", entry.entry_id, entry.ttl)

    async def get_entry(self, entry_id: str) -> CacheEntry | None:
        """
        Fetch an entry by id.  Returns None if the hash has expired or never existed.
        """
        raw = await self.client.hgetall(self._hash_key(entry_id))
        if not raw:
            return None
        try:
            return CacheEntry.from_redis_hash(raw)
        except (KeyError, ValueError) as exc:
            raise CacheCorruptionError(
                f"Cannot deserialise entry {entry_id}: {exc}"
            ) from exc

    async def delete_entry(self, entry_id: str) -> None:
        pipe = self.client.pipeline(transaction=True)
        pipe.delete(self._hash_key(entry_id))
        pipe.srem(self._index_key(), entry_id)
        await pipe.execute()
        logger.debug("Deleted entry %s", entry_id)

    async def entry_exists(self, entry_id: str) -> bool:
        return bool(await self.client.exists(self._hash_key(entry_id)))

    # ── Bulk / startup helpers ──────────────────────────────────────────

    async def all_entry_ids(self) -> set[str]:
        raw: set[bytes] = await self.client.smembers(self._index_key())
        return {eid.decode() if isinstance(eid, bytes) else eid for eid in raw}

    async def prune_stale_ids(self) -> int:
        """
        Remove entry_ids from the index Set whose hash keys no longer exist
        (expired between restart and now).  Called once at startup before
        rebuilding the in-memory index.
        """
        ids = await self.all_entry_ids()
        if not ids:
            return 0

        # Batch EXISTS check via pipeline
        pipe = self.client.pipeline(transaction=False)
        id_list = list(ids)
        for eid in id_list:
            pipe.exists(self._hash_key(eid))
        results = await pipe.execute()

        dead = [eid for eid, alive in zip(id_list, results) if not alive]
        if dead:
            await self.client.srem(self._index_key(), *dead)
            logger.info("Pruned %d stale entry ids from index Set.", len(dead))
        return len(dead)

    async def load_all_entries(self) -> list[CacheEntry]:
        """
        Load all live entries from Redis.  Called once at startup to rebuild
        the in-memory vector index.
        """
        ids = await self.all_entry_ids()
        if not ids:
            return []

        entries: list[CacheEntry] = []
        pipe = self.client.pipeline(transaction=False)
        id_list = list(ids)
        for eid in id_list:
            pipe.hgetall(self._hash_key(eid))
        results = await pipe.execute()

        for eid, raw in zip(id_list, results):
            if not raw:
                continue
            try:
                entries.append(CacheEntry.from_redis_hash(raw))
            except (KeyError, ValueError, CacheCorruptionError) as exc:
                logger.warning("Skipping corrupted entry %s: %s", eid, exc)

        logger.info("Loaded %d live entries from Redis.", len(entries))
        return entries

    async def flush(self, pattern_suffix: str = "*") -> int:
        """Delete all keys matching the prefix. Returns count of deleted keys."""
        keys = await self.client.keys(f"{self._prefix}:{pattern_suffix}")
        if keys:
            await self.client.delete(*keys)
        return len(keys)

    async def db_index(self) -> int:
        """Return the Redis database index this client is connected to."""
        try:
            info = await self.client.client_info()
            return int(info.get("db", 0))
        except ResponseError:
            # CLIENT INFO not available (Redis < 7.2); parse from connection URL instead
            from urllib.parse import urlparse
            parsed = urlparse(self._url)
            db = parsed.path.lstrip("/")
            return int(db) if db.isdigit() else 0
