"""
In-memory vector index using numpy cosine similarity.

Design notes
────────────
* Embeddings are stored **pre-normalised** (unit norm).  Cosine similarity
  then reduces to a single dot-product (matrix @ query_vec), executed by
  BLAS as a single DGEMV call — no per-pair division needed.

* An ``asyncio.Lock`` serialises all mutations (add / remove / rebuild).
  Searches acquire the same lock so they always see a consistent matrix.
  This is correct and lightweight because asyncio is single-threaded.

* ``np.argpartition`` gives O(N) top-K selection; only the K candidates
  are then sorted, keeping the hot path O(N) overall.
"""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from semantic_cache.store.schemas import CacheEntry

logger = logging.getLogger(__name__)

_EPSILON = 1e-10  # guard against zero-norm vectors


def _normalise(v: np.ndarray) -> np.ndarray:
    norm = np.linalg.norm(v)
    return v / (norm + _EPSILON)


class VectorIndex:
    """Thread-safe (asyncio) in-memory vector index."""

    def __init__(self, dim: int) -> None:
        self._dim = dim
        self._lock = asyncio.Lock()
        self._ids: list[str] = []
        self._matrix = np.empty((0, dim), dtype=np.float32)

    # ── Mutation (write) ───────────────────────────────────────────────

    async def add(self, entry_id: str, vector: np.ndarray) -> None:
        """Append a new entry.  ``vector`` need not be pre-normalised."""
        normed = _normalise(vector).astype(np.float32)
        async with self._lock:
            self._ids.append(entry_id)
            self._matrix = np.vstack(
                [self._matrix, normed[np.newaxis, :]]
            ) if self._matrix.shape[0] else normed[np.newaxis, :]

    async def remove(self, entry_id: str) -> bool:
        """Remove an entry by id.  Returns True if found and removed."""
        async with self._lock:
            try:
                idx = self._ids.index(entry_id)
            except ValueError:
                return False
            self._ids.pop(idx)
            self._matrix = np.delete(self._matrix, idx, axis=0)
            return True

    async def rebuild(self, entries: list["CacheEntry"]) -> None:
        """
        Replace the entire index atomically.  Called once at startup.
        Re-normalises stored embeddings defensively in case of float drift.
        """
        async with self._lock:
            if not entries:
                self._ids = []
                self._matrix = np.empty((0, self._dim), dtype=np.float32)
                return

            ids = [e.entry_id for e in entries]
            matrix = np.array([e.embedding for e in entries], dtype=np.float32)

            # Defensive normalisation
            norms = np.linalg.norm(matrix, axis=1, keepdims=True)
            norms = np.where(norms == 0, 1.0, norms)
            matrix = matrix / norms

            self._ids = ids
            self._matrix = matrix
        logger.info("VectorIndex rebuilt with %d entries.", len(ids))

    async def clear(self) -> None:
        async with self._lock:
            self._ids = []
            self._matrix = np.empty((0, self._dim), dtype=np.float32)

    # ── Search (read) ──────────────────────────────────────────────────

    async def search(
        self, query_vector: np.ndarray, top_k: int
    ) -> list[tuple[str, float]]:
        """
        Return up to ``top_k`` (entry_id, cosine_similarity) pairs,
        sorted by similarity descending.
        """
        normed_q = _normalise(query_vector).astype(np.float32)

        async with self._lock:
            n = self._matrix.shape[0]
            if n == 0:
                return []

            scores: np.ndarray = self._matrix @ normed_q  # shape (N,)

            k = min(top_k, n)
            if k == n:
                # All entries fit — sort directly
                order = np.argsort(scores)[::-1]
            else:
                # O(N) partial selection, then sort only k items
                part = np.argpartition(scores, -k)[-k:]
                order = part[np.argsort(scores[part])[::-1]]

            return [(self._ids[i], float(scores[i])) for i in order]

    # ── Introspection ──────────────────────────────────────────────────

    @property
    def size(self) -> int:
        return len(self._ids)

    @property
    def dim(self) -> int:
        return self._dim
