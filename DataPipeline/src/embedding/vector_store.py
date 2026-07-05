"""FAISS-backed vector store with persistence and metadata indexing."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Optional

import numpy as np

from src.models.schemas import EmbeddingRecord
from src.utils.logger import get_logger

logger = get_logger(__name__)


class FAISSVectorStore:
    """Persistent FAISS vector store compatible with Pinecone-ready JSON exports.

    Stores embeddings with chunk_id / doc_id metadata for full traceability.
    """

    def __init__(self, save_path: str = "./output/embeddings", dimensions: int = 384) -> None:
        self.save_path = Path(save_path)
        self.save_path.mkdir(parents=True, exist_ok=True)
        self.dimensions = dimensions
        self._index: Any = None
        self._metadata: list[dict[str, str]] = []
        self._index_file = self.save_path / "faiss.index"
        self._meta_file = self.save_path / "metadata.json"
        self._load_existing()

    def _get_faiss(self):
        try:
            import faiss
            return faiss
        except ImportError as e:
            raise ImportError("faiss-cpu not installed. Run: pip install faiss-cpu") from e

    def _load_existing(self) -> None:
        faiss = self._get_faiss()
        if self._index_file.exists():
            self._index = faiss.read_index(str(self._index_file))
            logger.info("faiss_index_loaded", vectors=self._index.ntotal)
        else:
            self._index = faiss.IndexFlatL2(self.dimensions)

        if self._meta_file.exists():
            with self._meta_file.open("r") as f:
                self._metadata = json.load(f)

    def add(self, records: list[EmbeddingRecord]) -> None:
        """Add embedding records to the FAISS index."""
        if not records:
            return

        faiss = self._get_faiss()
        vectors = np.array([r.embedding for r in records], dtype=np.float32)

        if vectors.shape[1] != self.dimensions:
            raise ValueError(
                f"Dimension mismatch: expected {self.dimensions}, got {vectors.shape[1]}"
            )

        self._index.add(vectors)
        for r in records:
            self._metadata.append(
                {"chunk_id": r.chunk_id, "doc_id": r.doc_id, "model": r.model}
            )

        self._persist()
        logger.info("vectors_added", count=len(records), total=self._index.ntotal)

    def search(
        self, query_vector: np.ndarray, top_k: int = 10
    ) -> list[dict[str, Any]]:
        """Return top_k nearest neighbours with metadata."""
        faiss = self._get_faiss()
        query = np.array([query_vector], dtype=np.float32)
        distances, indices = self._index.search(query, top_k)

        results: list[dict[str, Any]] = []
        for dist, idx in zip(distances[0], indices[0]):
            if idx < 0 or idx >= len(self._metadata):
                continue
            meta = self._metadata[idx]
            results.append({**meta, "distance": float(dist), "index": int(idx)})
        return results

    def _persist(self) -> None:
        faiss = self._get_faiss()
        faiss.write_index(self._index, str(self._index_file))
        with self._meta_file.open("w") as f:
            json.dump(self._metadata, f, indent=2)

    def export_pinecone_format(self, records: list[EmbeddingRecord]) -> list[dict[str, Any]]:
        """Export embeddings in Pinecone-compatible upsert format."""
        return [
            {
                "id": r.chunk_id,
                "values": r.embedding,
                "metadata": {"doc_id": r.doc_id, "model": r.model},
            }
            for r in records
        ]

    @property
    def total_vectors(self) -> int:
        return self._index.ntotal if self._index else 0
