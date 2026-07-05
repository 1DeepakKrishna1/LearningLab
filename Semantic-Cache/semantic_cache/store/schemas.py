"""Pydantic models for cache entries and search results."""

from __future__ import annotations

import time
import uuid
from typing import Any

from pydantic import BaseModel, Field


class CacheEntry(BaseModel):
    entry_id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    question: str
    answer: str
    embedding: list[float]
    created_at: float = Field(default_factory=time.time)
    ttl: int = Field(default=3600, description="Original TTL in seconds; 0 = no expiry")
    model_used: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)

    def to_redis_hash(self) -> dict[str, str]:
        """Serialise to a flat dict of strings suitable for HSET."""
        import json

        return {
            "entry_id": self.entry_id,
            "question": self.question,
            "answer": self.answer,
            "embedding": json.dumps(self.embedding),
            "created_at": str(self.created_at),
            "ttl": str(self.ttl),
            "model_used": self.model_used,
            "metadata": json.dumps(self.metadata),
        }

    @classmethod
    def from_redis_hash(cls, data: dict[bytes | str, bytes | str]) -> "CacheEntry":
        """Deserialise from a raw HGETALL result."""
        import json

        def _s(v: bytes | str) -> str:
            return v.decode() if isinstance(v, bytes) else v

        d = {(_s(k)): _s(v) for k, v in data.items()}
        return cls(
            entry_id=d["entry_id"],
            question=d["question"],
            answer=d["answer"],
            embedding=json.loads(d["embedding"]),
            created_at=float(d["created_at"]),
            ttl=int(d["ttl"]),
            model_used=d.get("model_used", ""),
            metadata=json.loads(d.get("metadata", "{}")),
        )


class SearchResult(BaseModel):
    entry: CacheEntry
    similarity: float


class CacheResponse(BaseModel):
    strategy: str  # "direct_hit" | "rag_generation" | "llm_fallback"
    answer: str
    latency_ms: float
    source_entry_id: str | None = None
    similarity: float | None = None
    context_count: int = 0
