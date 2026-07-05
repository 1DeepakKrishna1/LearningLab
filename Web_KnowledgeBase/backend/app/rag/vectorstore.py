"""FAISS-backed vector index with a parallel metadata list, persisted to disk."""
from __future__ import annotations

import json
import os
import threading
from dataclasses import asdict, dataclass

import faiss
import numpy as np


@dataclass
class ChunkRecord:
    page_id: str
    chunk_id: str
    url: str
    title: str
    text: str


class VectorStore:
    def __init__(self, dim: int) -> None:
        self.dim = dim
        self.index = faiss.IndexFlatIP(dim)
        self.records: list[ChunkRecord] = []
        self._lock = threading.Lock()

    def add(self, vectors: np.ndarray, records: list[ChunkRecord]) -> None:
        if len(records) == 0:
            return
        with self._lock:
            self.index.add(vectors.astype("float32"))
            self.records.extend(records)

    def search(self, query_vec: np.ndarray, top_k: int) -> list[tuple[float, ChunkRecord]]:
        if self.index.ntotal == 0:
            return []
        q = query_vec.astype("float32").reshape(1, -1)
        k = min(top_k, self.index.ntotal)
        scores, idxs = self.index.search(q, k)
        out: list[tuple[float, ChunkRecord]] = []
        for score, idx in zip(scores[0], idxs[0]):
            if idx == -1:
                continue
            out.append((float(score), self.records[idx]))
        return out

    def remove_pages(self, page_ids: set[str]) -> int:
        """Drop all chunks whose page_id is in page_ids; rebuild the index. Returns count removed."""
        with self._lock:
            keep = [i for i, r in enumerate(self.records) if r.page_id not in page_ids]
            removed = len(self.records) - len(keep)
            if removed == 0:
                return 0
            new_index = faiss.IndexFlatIP(self.dim)
            if keep:
                allv = self.index.reconstruct_n(0, self.index.ntotal)
                new_index.add(np.asarray(allv)[keep].astype("float32"))
            self.index = new_index
            self.records = [self.records[i] for i in keep]
            return removed

    @property
    def size(self) -> int:
        return self.index.ntotal

    # ---- persistence ----
    def save(self, directory: str) -> None:
        os.makedirs(directory, exist_ok=True)
        faiss.write_index(self.index, os.path.join(directory, "index.faiss"))
        with open(os.path.join(directory, "records.json"), "w", encoding="utf-8") as f:
            json.dump(
                {"dim": self.dim, "records": [asdict(r) for r in self.records]},
                f,
                ensure_ascii=False,
            )

    @classmethod
    def load(cls, directory: str) -> "VectorStore":
        with open(os.path.join(directory, "records.json"), "r", encoding="utf-8") as f:
            data = json.load(f)
        store = cls(dim=data["dim"])
        store.index = faiss.read_index(os.path.join(directory, "index.faiss"))
        store.records = [ChunkRecord(**r) for r in data["records"]]
        return store

    @staticmethod
    def exists(directory: str) -> bool:
        return os.path.exists(os.path.join(directory, "index.faiss")) and os.path.exists(
            os.path.join(directory, "records.json")
        )
