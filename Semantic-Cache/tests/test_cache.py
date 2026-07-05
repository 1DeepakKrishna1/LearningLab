"""
Integration tests for SemanticCache.

Requires a live Redis instance at REDIS_URL (default: redis://localhost:6379/0).
Uses a mock embedder (no external API calls) and a mock LLM caller.

Run with::

    pytest tests/test_cache.py -v -m integration
"""

from __future__ import annotations

import asyncio
from typing import Any
from unittest.mock import AsyncMock

import numpy as np
import pytest
import pytest_asyncio

from semantic_cache.cache import LLMCallerProtocol, SemanticCache
from semantic_cache.config import Settings
from semantic_cache.embedders import EmbedderProtocol
from semantic_cache.index.vector_index import VectorIndex
from semantic_cache.store.redis_store import RedisStore


# ── Fixtures ────────────────────────────────────────────────────────────────────


class FixedEmbedder:
    """
    Deterministic embedder: maps known phrases to fixed unit-norm 4-D vectors.
    Unknown phrases return a random (seeded) vector.
    """

    _MAP: dict[str, list[float]] = {
        "what is python":       [1.0, 0.0, 0.0, 0.0],
        "tell me about python": [0.95, 0.31, 0.0, 0.0],   # similar to above
        "what is java":         [0.0, 1.0, 0.0, 0.0],
        "capital of france":    [0.0, 0.0, 1.0, 0.0],
        "capital of germany":   [0.0, 0.0, 0.95, 0.31],   # similar to above
        "random unrelated":     [0.0, 0.0, 0.0, 1.0],
    }

    @property
    def dim(self) -> int:
        return 4

    async def embed_one(self, text: str) -> np.ndarray:
        normed_text = text.lower().strip()
        vec = self._MAP.get(normed_text, [0.5, 0.5, 0.5, 0.5])
        arr = np.array(vec, dtype=np.float32)
        return arr / np.linalg.norm(arr)

    async def embed_many(self, texts: list[str]) -> list[np.ndarray]:
        return [await self.embed_one(t) for t in texts]


class MockLLMCaller:
    def __init__(self, answer: str = "mock answer") -> None:
        self._answer = answer
        self.generate_calls: list[str] = []
        self.generate_ctx_calls: list[tuple] = []

    @property
    def model_name(self) -> str:
        return "mock-llm"

    async def generate(self, question: str) -> str:
        self.generate_calls.append(question)
        return self._answer

    async def generate_with_context(
        self, question: str, context: list[tuple[str, str]]
    ) -> str:
        self.generate_ctx_calls.append((question, context))
        return f"rag: {self._answer}"


@pytest_asyncio.fixture
async def cache(unique_prefix: str):
    settings = Settings(
        REDIS_URL="redis://localhost:6379/0",
        KEY_PREFIX=unique_prefix,
        HIGH_TH=0.9,
        LOW_TH=0.7,
        TOP_K=5,
        DEFAULT_TTL=60,
        EMBEDDING_PROVIDER="openai",  # overridden by FixedEmbedder
        VECTOR_DIM=4,
    )
    embedder = FixedEmbedder()
    store = RedisStore(redis_url=settings.redis_url, key_prefix=settings.key_prefix)
    index = VectorIndex(dim=4)

    instance = SemanticCache(settings=settings, embedder=embedder, store=store, index=index)
    await instance._startup()

    yield instance

    await instance.flush()
    await instance.shutdown()


# ── Strategy: llm_fallback ──────────────────────────────────────────────────────


@pytest.mark.asyncio
@pytest.mark.integration
async def test_llm_fallback_on_empty_cache(cache: SemanticCache) -> None:
    llm = MockLLMCaller("Python is a programming language.")
    resp = await cache.query("what is python", llm)

    assert resp.strategy == "llm_fallback"
    assert resp.answer == "Python is a programming language."
    assert len(llm.generate_calls) == 1
    assert len(llm.generate_ctx_calls) == 0


# ── Strategy: direct_hit ────────────────────────────────────────────────────────


@pytest.mark.asyncio
@pytest.mark.integration
async def test_direct_hit_exact_repeat(cache: SemanticCache) -> None:
    llm = MockLLMCaller("Python is a programming language.")
    # First query — populates cache
    await cache.query("what is python", llm)
    llm.generate_calls.clear()

    # Second identical query — should be a direct hit
    resp = await cache.query("what is python", llm)

    assert resp.strategy == "direct_hit"
    assert resp.similarity is not None
    assert resp.similarity >= 0.9
    assert len(llm.generate_calls) == 0  # no LLM call
    assert len(llm.generate_ctx_calls) == 0


# ── Strategy: rag_generation ────────────────────────────────────────────────────


@pytest.mark.asyncio
@pytest.mark.integration
async def test_rag_on_similar_query(cache: SemanticCache) -> None:
    llm = MockLLMCaller("Python is a high-level language.")
    # Seed the cache with "what is python" (sim=1.0 to itself)
    await cache.query("what is python", llm)
    llm.generate_calls.clear()
    llm.generate_ctx_calls.clear()

    # "tell me about python" is similar but not identical (sim ≈ 0.95)
    # → should trigger RAG, not direct hit
    resp = await cache.query("tell me about python", llm)

    assert resp.strategy == "rag_generation"
    assert resp.context_count >= 1
    assert "rag:" in resp.answer
    assert len(llm.generate_ctx_calls) == 1


# ── Manual set / invalidate ─────────────────────────────────────────────────────


@pytest.mark.asyncio
@pytest.mark.integration
async def test_manual_set_and_direct_hit(cache: SemanticCache) -> None:
    entry_id = await cache.set("what is python", "A serpentine language.")

    llm = MockLLMCaller()
    resp = await cache.query("what is python", llm)

    assert resp.strategy == "direct_hit"
    assert resp.answer == "A serpentine language."
    assert resp.source_entry_id == entry_id


@pytest.mark.asyncio
@pytest.mark.integration
async def test_invalidate_entry(cache: SemanticCache) -> None:
    entry_id = await cache.set("what is python", "Python is X.")
    removed = await cache.invalidate(entry_id)
    assert removed is True

    # After invalidation the cache should fall back to LLM
    llm = MockLLMCaller("fresh answer")
    resp = await cache.query("what is python", llm)
    assert resp.strategy == "llm_fallback"


# ── TTL / stale index guard ──────────────────────────────────────────────────────


@pytest.mark.asyncio
@pytest.mark.integration
async def test_stale_index_cleaned_on_read(cache: SemanticCache) -> None:
    """
    Store an entry with TTL=1, wait for it to expire.
    The index still holds the stale id (listener may not have fired).
    A subsequent query should detect the stale entry and fall through to LLM.
    """
    entry_id = await cache.set("capital of france", "Paris.", ttl=1)
    await asyncio.sleep(2)  # let Redis expire the key

    llm = MockLLMCaller("Paris!")
    resp = await cache.query("capital of france", llm)

    # Must NOT return a direct hit from the stale index entry
    assert resp.strategy != "direct_hit"
    # The stale id should have been purged from the index
    assert cache._index.size == 0 or entry_id not in cache._index._ids


# ── Stats ────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
@pytest.mark.integration
async def test_stats(cache: SemanticCache) -> None:
    stats = await cache.stats()
    assert "index_size" in stats
    assert "high_th" in stats
    assert stats["high_th"] == pytest.approx(0.9)


# ── Flush ────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
@pytest.mark.integration
async def test_flush(cache: SemanticCache) -> None:
    llm = MockLLMCaller()
    await cache.query("what is python", llm)
    await cache.query("what is java", llm)

    count = await cache.flush()
    assert count >= 2
    assert cache._index.size == 0

    # After flush, next query must be llm_fallback
    resp = await cache.query("what is python", llm)
    assert resp.strategy == "llm_fallback"


# ── Latency field ─────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
@pytest.mark.integration
async def test_latency_ms_positive(cache: SemanticCache) -> None:
    llm = MockLLMCaller()
    resp = await cache.query("what is python", llm)
    assert resp.latency_ms > 0
