"""
SemanticCache — the public-facing orchestrator.

Hybrid retrieval strategy
─────────────────────────
Given a query ``q`` and the current cache:

  1. Embed ``q`` → unit-norm vector.
  2. Search the in-memory index for top-K candidates by cosine similarity.
  3. Validate each candidate against Redis (stale-index guard).
  4. Decision tree:

     top-1 similarity ≥ HIGH_TH (0.9)
         → DIRECT HIT: return the cached answer unchanged.

     elif ANY candidate similarity ≥ LOW_TH (0.7)
         → RAG GENERATION: pass the top-K Q/A pairs as context to the LLM
           and generate a fresh, contextualised answer.  Cache the result.

     else
         → LLM FALLBACK: call the LLM with no cache context.  Cache the result.

No stale index problem
──────────────────────
* ``ExpiryListener`` (background task) removes vectors from the index when
  Redis fires ``keyevent:expired`` notifications.
* Even if the listener lags, every candidate is validated with a Redis
  ``HGETALL`` before use; stale ids are removed from the index on the spot.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any, Protocol, runtime_checkable

import numpy as np

from semantic_cache.config import Settings
from semantic_cache.embedders import EmbedderProtocol, build_embedder
from semantic_cache.exceptions import VectorDimensionMismatch
from semantic_cache.index.vector_index import VectorIndex
from semantic_cache.listener import ExpiryListener
from semantic_cache.store.redis_store import RedisStore
from semantic_cache.store.schemas import CacheEntry, CacheResponse, SearchResult

logger = logging.getLogger(__name__)


# ── LLM caller protocol ────────────────────────────────────────────────────────


@runtime_checkable
class LLMCallerProtocol(Protocol):
    async def generate(self, question: str) -> str: ...

    async def generate_with_context(
        self,
        question: str,
        context: list[tuple[str, str]],
    ) -> str: ...

    @property
    def model_name(self) -> str: ...


# ── Groq LLM caller ────────────────────────────────────────────────────────────


class GroqLLMCaller:
    """
    LLM caller backed by Groq's ultra-fast inference API.

    Groq exposes an OpenAI-compatible interface via the ``groq`` SDK.
    Default model: ``llama-3.3-70b-versatile`` (strong general-purpose model
    available on Groq at time of writing; override via ``model`` parameter or
    ``LLM_MODEL`` env var).

    Usage::

        from semantic_cache import GroqLLMCaller, SemanticCache, Settings

        settings = Settings()   # GROQ_API_KEY read from .env
        llm = GroqLLMCaller.from_settings(settings)

        async with SemanticCache.create(settings) as cache:
            resp = await cache.query("What is Python?", llm)
    """

    DEFAULT_MODEL = "llama-3.3-70b-versatile"

    def __init__(
        self,
        model: str = DEFAULT_MODEL,
        max_tokens: int = 1024,
        api_key: str | None = None,
    ) -> None:
        self._api_key = api_key  # resolved lazily; may also come from GROQ_API_KEY env var
        self._model = model
        self._max_tokens = max_tokens
        self.__client: Any = None  # created on first use

    @property
    def _client(self) -> Any:
        if self.__client is None:
            from groq import AsyncGroq

            self.__client = (
                AsyncGroq(api_key=self._api_key) if self._api_key else AsyncGroq()
            )
        return self.__client

    @property
    def model_name(self) -> str:
        return self._model

    async def generate(self, question: str) -> str:
        return await self._chat([{"role": "user", "content": question}])

    async def generate_with_context(
        self,
        question: str,
        context: list[tuple[str, str]],
    ) -> str:
        ctx_block = "\n\n".join(f"Q: {q}\nA: {a}" for q, a in context)
        system_prompt = (
            "You are a helpful assistant. Use the related Q&A pairs below as "
            "context to answer the user's question accurately and concisely.\n\n"
            f"Related Q&A pairs:\n{ctx_block}"
        )
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": question},
        ]
        return await self._chat(messages)

    async def _chat(self, messages: list[dict]) -> str:
        response = await self._client.chat.completions.create(
            model=self._model,
            messages=messages,
            max_tokens=self._max_tokens,
        )
        return response.choices[0].message.content or ""

    @classmethod
    def from_settings(cls, settings: "Settings") -> "GroqLLMCaller":
        return cls(
            model=settings.llm_model,
            max_tokens=settings.llm_max_tokens,
            api_key=settings.groq_api_key or None,
        )


# ── Main cache class ───────────────────────────────────────────────────────────


class SemanticCache:
    """
    Production semantic cache with hybrid retrieval and TTL-based expiry.

    Typical usage::

        settings = Settings()
        async with SemanticCache.create(settings) as cache:
            response = await cache.query("What is Python?", llm_caller)
            print(response.answer, response.strategy)
    """

    def __init__(
        self,
        settings: Settings,
        embedder: EmbedderProtocol,
        store: RedisStore,
        index: VectorIndex,
    ) -> None:
        self._settings = settings
        self._embedder = embedder
        self._store = store
        self._index = index
        self._listener: ExpiryListener | None = None
        self._listener_task: asyncio.Task | None = None
        self._initialized = False

    # ── Factory / lifecycle ────────────────────────────────────────────

    @classmethod
    async def create(
        cls,
        settings: Settings | None = None,
        embedder: EmbedderProtocol | None = None,
    ) -> "SemanticCache":
        """
        Async factory.  Connects to Redis, validates embedding dimension,
        rebuilds the vector index, and starts the expiry listener.

        Prefer using as an async context manager::

            async with SemanticCache.create(settings) as cache:
                ...
        """
        cfg = settings or Settings()
        emb = embedder or build_embedder(cfg)

        # Validate embedding dimension at startup
        await cls._check_dim(emb, cfg.vector_dim)

        store = RedisStore(redis_url=cfg.redis_url, key_prefix=cfg.key_prefix)
        index = VectorIndex(dim=cfg.vector_dim)

        instance = cls(settings=cfg, embedder=emb, store=store, index=index)
        await instance._startup()
        return instance

    async def _startup(self) -> None:
        if self._initialized:
            return
        self._initialized = True
        await self._store.connect()
        await self._store.enable_keyspace_notifications()

        # Prune stale membership Set entries from previous runs
        pruned = await self._store.prune_stale_ids()
        if pruned:
            logger.info("Pruned %d stale entry ids at startup.", pruned)

        # Rebuild index from Redis
        entries = await self._store.load_all_entries()
        await self._index.rebuild(entries)
        logger.info("SemanticCache started — index size: %d.", self._index.size)

        # Determine Redis DB for keyspace channel
        db = await self._store.db_index()

        # Start expiry listener as a background task
        self._listener = ExpiryListener(store=self._store, index=self._index)
        self._listener_task = asyncio.create_task(
            self._listener.run(db_index=db),
            name="semcache-expiry-listener",
        )

    async def shutdown(self) -> None:
        if self._listener_task and not self._listener_task.done():
            self._listener_task.cancel()
            await asyncio.gather(self._listener_task, return_exceptions=True)
        await self._store.close()
        logger.info("SemanticCache shut down.")

    async def __aenter__(self) -> "SemanticCache":
        await self._startup()
        return self

    async def __aexit__(self, *_: Any) -> None:
        await self.shutdown()

    # ── Core API ───────────────────────────────────────────────────────

    async def query(
        self,
        question: str,
        llm_caller: LLMCallerProtocol,
        *,
        ttl: int | None = None,
    ) -> CacheResponse:
        """
        Retrieve an answer for ``question`` using the hybrid strategy.

        Args:
            question:   The user's question text.
            llm_caller: Async LLM interface (generate / generate_with_context).
            ttl:        Override default TTL for any new cache entry created.

        Returns:
            ``CacheResponse`` with ``strategy``, ``answer``, ``latency_ms``,
            and optional provenance fields.
        """
        t0 = time.perf_counter()
        cfg = self._settings

        # ── Step 1: embed ───────────────────────────────────────────────
        q_vec = await self._embedder.embed_one(self._normalize(question))

        # ── Step 2: search ──────────────────────────────────────────────
        raw_candidates = await self._index.search(q_vec, top_k=cfg.top_k)

        # ── Step 3: validate (stale-index guard) ────────────────────────
        candidates = await self._validate_candidates(raw_candidates)

        # ── Step 4: hybrid strategy ─────────────────────────────────────
        effective_ttl = ttl if ttl is not None else cfg.default_ttl

        if candidates:
            top = candidates[0]

            if top.similarity >= cfg.high_th:
                # ── DIRECT HIT ──────────────────────────────────────────
                logger.info(
                    "direct_hit sim=%.4f entry=%s query=%.60s",
                    top.similarity,
                    top.entry.entry_id,
                    question,
                )
                return CacheResponse(
                    strategy="direct_hit",
                    answer=top.entry.answer,
                    latency_ms=_ms(t0),
                    source_entry_id=top.entry.entry_id,
                    similarity=top.similarity,
                )

            rag_candidates = [c for c in candidates if c.similarity >= cfg.low_th]
            if rag_candidates:
                # ── RAG GENERATION ──────────────────────────────────────
                context = [(c.entry.question, c.entry.answer) for c in rag_candidates]
                answer = await llm_caller.generate_with_context(question, context)
                await self._store_new(
                    question, q_vec, answer, llm_caller.model_name, effective_ttl
                )
                logger.info(
                    "rag_generation ctx=%d top_sim=%.4f query=%.60s",
                    len(context),
                    rag_candidates[0].similarity,
                    question,
                )
                return CacheResponse(
                    strategy="rag_generation",
                    answer=answer,
                    latency_ms=_ms(t0),
                    similarity=rag_candidates[0].similarity,
                    context_count=len(context),
                )

        # ── LLM FALLBACK ────────────────────────────────────────────────
        answer = await llm_caller.generate(question)
        await self._store_new(
            question, q_vec, answer, llm_caller.model_name, effective_ttl
        )
        logger.info("llm_fallback query=%.60s", question)
        logger.info("llm_fallback answer=%.100s", answer)
        return CacheResponse(
            strategy="llm_fallback",
            answer=answer,
            latency_ms=_ms(t0),
        )

    async def set(
        self,
        question: str,
        answer: str,
        *,
        metadata: dict[str, Any] | None = None,
        ttl: int | None = None,
    ) -> str:
        """Manually insert an entry.  Returns the new entry_id."""
        q_vec = await self._embedder.embed_one(self._normalize(question))
        effective_ttl = ttl if ttl is not None else self._settings.default_ttl
        entry = await self._store_new(
            question, q_vec, answer, model_used="manual",
            ttl=effective_ttl, metadata=metadata,
        )
        return entry.entry_id

    async def invalidate(self, entry_id: str) -> bool:
        """Remove a specific entry from Redis and the index."""
        await self._store.delete_entry(entry_id)
        return await self._index.remove(entry_id)

    async def flush(self) -> int:
        """Delete all cache entries.  Returns count of deleted Redis keys."""
        count = await self._store.flush()
        await self._index.clear()
        logger.info("Cache flushed (%d keys deleted).", count)
        return count

    async def stats(self) -> dict[str, Any]:
        return {
            "index_size": self._index.size,
            "high_th": self._settings.high_th,
            "low_th": self._settings.low_th,
            "top_k": self._settings.top_k,
            "default_ttl": self._settings.default_ttl,
            "hf_model_name": self._settings.hf_model_name,
            "vector_dim": self._settings.vector_dim,
        }

    # ── Internal helpers ───────────────────────────────────────────────

    async def _validate_candidates(
        self,
        raw: list[tuple[str, float]],
    ) -> list[SearchResult]:
        """
        For each candidate returned by the index:
        - Fetch the full entry from Redis.
        - If the entry is gone (expired), remove it from the index immediately.
        Returns only live candidates as ``SearchResult`` objects.
        """
        if not raw:
            return []

        # Parallel fetches
        tasks = [self._store.get_entry(eid) for eid, _ in raw]
        fetched = await asyncio.gather(*tasks, return_exceptions=True)

        results: list[SearchResult] = []
        for (entry_id, score), entry_or_exc in zip(raw, fetched):
            if isinstance(entry_or_exc, Exception):
                logger.warning(
                    "Error fetching candidate %s: %s", entry_id, entry_or_exc
                )
                continue
            if entry_or_exc is None:
                # Key expired; listener may not have fired yet
                logger.debug("Stale index entry detected: %s — removing.", entry_id)
                await self._index.remove(entry_id)
                continue
            results.append(SearchResult(entry=entry_or_exc, similarity=score))

        return results

    async def _store_new(
        self,
        question: str,
        q_vec: np.ndarray,
        answer: str,
        model_used: str,
        ttl: int,
        metadata: dict[str, Any] | None = None,
    ) -> CacheEntry:
        entry = CacheEntry(
            question=question,
            answer=answer,
            embedding=q_vec.tolist(),
            ttl=ttl,
            model_used=model_used,
            metadata=metadata or {},
        )
        # Write to Redis first — if the process crashes before index.add(),
        # the cold-start rebuild will recover the entry from Redis.
        await self._store.save_entry(entry)
        await self._index.add(entry.entry_id, q_vec)
        logger.debug("Cached new entry %s (ttl=%ds).", entry.entry_id, ttl)
        return entry

    # ── Static helpers ─────────────────────────────────────────────────

    @staticmethod
    def _normalize(text: str) -> str:
        """Lowercase and strip whitespace/trailing punctuation before embedding.

        Ensures "What is Python?", "what is python", and "What is Python"
        all resolve to the same vector, improving cache hit rates.
        """
        return text.lower().strip().rstrip("?!.,;:")

    @staticmethod
    async def _check_dim(embedder: EmbedderProtocol, expected_dim: int) -> None:
        """
        Embed a dummy text and verify the output dimension matches config.
        Raises ``VectorDimensionMismatch`` on mismatch to prevent silent corruption.
        """
        probe = await embedder.embed_one("dimension check probe")
        actual = probe.shape[0]
        if actual != expected_dim:
            raise VectorDimensionMismatch(expected=expected_dim, actual=actual)


# ── Utility ────────────────────────────────────────────────────────────────────


def _ms(t0: float) -> float:
    return (time.perf_counter() - t0) * 1000
