"""Unit tests for VectorIndex — no Redis required."""

from __future__ import annotations

import asyncio

import numpy as np
import pytest

from semantic_cache.index.vector_index import VectorIndex


@pytest.fixture
def index() -> VectorIndex:
    return VectorIndex(dim=4)


# ── Basic CRUD ──────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_add_and_size(index: VectorIndex) -> None:
    await index.add("a", np.array([1, 0, 0, 0], dtype=np.float32))
    assert index.size == 1
    await index.add("b", np.array([0, 1, 0, 0], dtype=np.float32))
    assert index.size == 2


@pytest.mark.asyncio
async def test_remove_existing(index: VectorIndex) -> None:
    await index.add("a", np.array([1, 0, 0, 0], dtype=np.float32))
    removed = await index.remove("a")
    assert removed is True
    assert index.size == 0


@pytest.mark.asyncio
async def test_remove_missing(index: VectorIndex) -> None:
    removed = await index.remove("nonexistent")
    assert removed is False


@pytest.mark.asyncio
async def test_clear(index: VectorIndex) -> None:
    for i in range(5):
        v = np.zeros(4, dtype=np.float32)
        v[i % 4] = 1.0
        await index.add(str(i), v)
    await index.clear()
    assert index.size == 0


# ── Search correctness ──────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_search_exact_match(index: VectorIndex) -> None:
    """Querying with the same vector as a stored entry should yield score ≈ 1.0."""
    v = np.array([1, 0, 0, 0], dtype=np.float32)
    await index.add("exact", v)
    results = await index.search(v, top_k=1)
    assert len(results) == 1
    entry_id, score = results[0]
    assert entry_id == "exact"
    assert score == pytest.approx(1.0, abs=1e-5)


@pytest.mark.asyncio
async def test_search_orthogonal_zero(index: VectorIndex) -> None:
    """Orthogonal vectors have cosine similarity 0."""
    await index.add("a", np.array([1, 0, 0, 0], dtype=np.float32))
    query = np.array([0, 1, 0, 0], dtype=np.float32)
    results = await index.search(query, top_k=1)
    assert results[0][1] == pytest.approx(0.0, abs=1e-5)


@pytest.mark.asyncio
async def test_search_ranking(index: VectorIndex) -> None:
    """Results should be sorted by descending similarity."""
    await index.add("hi", np.array([0.9, 0.1, 0, 0], dtype=np.float32))
    await index.add("lo", np.array([0.1, 0.9, 0, 0], dtype=np.float32))
    query = np.array([1, 0, 0, 0], dtype=np.float32)
    results = await index.search(query, top_k=2)
    assert results[0][0] == "hi"
    assert results[1][0] == "lo"
    assert results[0][1] > results[1][1]


@pytest.mark.asyncio
async def test_search_top_k_capped(index: VectorIndex) -> None:
    for i in range(3):
        v = np.zeros(4, dtype=np.float32)
        v[i] = 1.0
        await index.add(str(i), v)
    results = await index.search(np.array([1, 0, 0, 0], dtype=np.float32), top_k=10)
    assert len(results) == 3  # capped at index size


@pytest.mark.asyncio
async def test_search_empty_index(index: VectorIndex) -> None:
    results = await index.search(np.array([1, 0, 0, 0], dtype=np.float32), top_k=5)
    assert results == []


# ── Rebuild ─────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_rebuild_replaces_index(index: VectorIndex) -> None:
    await index.add("old", np.array([1, 0, 0, 0], dtype=np.float32))

    from semantic_cache.store.schemas import CacheEntry

    new_entries = [
        CacheEntry(
            entry_id="new1",
            question="q",
            answer="a",
            embedding=[0.0, 1.0, 0.0, 0.0],
        )
    ]
    await index.rebuild(new_entries)
    assert index.size == 1
    results = await index.search(np.array([0, 1, 0, 0], dtype=np.float32), top_k=1)
    assert results[0][0] == "new1"


@pytest.mark.asyncio
async def test_rebuild_empty(index: VectorIndex) -> None:
    await index.add("x", np.array([1, 0, 0, 0], dtype=np.float32))
    await index.rebuild([])
    assert index.size == 0


# ── Concurrency ──────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_concurrent_adds(index: VectorIndex) -> None:
    """Multiple concurrent adds should not corrupt the index."""
    async def add_entry(i: int) -> None:
        v = np.zeros(4, dtype=np.float32)
        v[i % 4] = 1.0
        await index.add(f"entry_{i}", v)

    await asyncio.gather(*[add_entry(i) for i in range(50)])
    assert index.size == 50


@pytest.mark.asyncio
async def test_concurrent_add_and_remove(index: VectorIndex) -> None:
    """Concurrent adds and removes should leave a consistent state."""
    for i in range(20):
        v = np.zeros(4, dtype=np.float32)
        v[i % 4] = 1.0
        await index.add(f"e{i}", v)

    async def remove_some() -> None:
        for i in range(0, 20, 2):
            await index.remove(f"e{i}")

    async def search_some() -> None:
        for _ in range(10):
            await index.search(np.array([1, 0, 0, 0], dtype=np.float32), top_k=3)
            await asyncio.sleep(0)

    await asyncio.gather(remove_some(), search_some())
    assert index.size == 10  # 10 even-indexed entries removed


# ── Normalisation ────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_unnormalised_input_handled(index: VectorIndex) -> None:
    """Vectors that are not unit-norm should still yield correct scores."""
    v = np.array([3, 4, 0, 0], dtype=np.float32)  # norm = 5
    await index.add("scaled", v)
    query = np.array([1, 0, 0, 0], dtype=np.float32)
    results = await index.search(query, top_k=1)
    # cos([3,4,0,0], [1,0,0,0]) = 3/5 = 0.6
    assert results[0][1] == pytest.approx(0.6, abs=1e-5)
