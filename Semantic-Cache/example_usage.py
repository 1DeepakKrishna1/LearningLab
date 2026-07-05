"""
Runnable example demonstrating SemanticCache with a configurable LLM backend.

LLM backend is selected via the LLM_BACKEND env var (default: ``mock``):

  LLM_BACKEND=mock   — deterministic in-process mock, no API key needed
  LLM_BACKEND=groq   — Groq API (requires GROQ_API_KEY in .env)

Other env vars (all optional, loaded from .env):
  REDIS_URL      — default redis://localhost:6379/0 (falls back to fakeredis)
  GROQ_API_KEY   — required only when LLM_BACKEND=groq
  LLM_MODEL      — Groq model name (default llama-3.3-70b-versatile)
  LLM_MAX_TOKENS — max tokens for Groq responses (default 1024)

Usage::

    python example_usage.py

    # Use Groq:
    LLM_BACKEND=groq python example_usage.py

    # Against a real Redis:
    REDIS_URL=redis://localhost:6379/0 python example_usage.py
"""

from __future__ import annotations

import asyncio
import logging
import os

import numpy as np

from semantic_cache import GroqLLMCaller, SemanticCache, Settings
from semantic_cache.embedders import HuggingFaceEmbedder
from semantic_cache.index.vector_index import VectorIndex
from semantic_cache.store.redis_store import RedisStore

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")


def _make_redis_client(url: str):
    """Return a real or fake async Redis client, falling back to fakeredis."""
    import redis.asyncio as aioredis

    try:
        import socket
        from urllib.parse import urlparse

        p = urlparse(url)
        host, port = p.hostname or "localhost", p.port or 6379
        with socket.create_connection((host, port), timeout=1):
            pass
        return aioredis.from_url(url, decode_responses=False, socket_keepalive=True)
    except OSError:
        import fakeredis.aioredis as fakeredis

        print("  [demo] Redis not reachable — using in-memory fakeredis\n")
        return fakeredis.FakeRedis(decode_responses=False)


# ── Mock LLM (no Groq API key needed for this example) ────────────────────────


class MockLLM:
    """Returns canned answers; counts real calls so we can verify cache hits."""

    call_count = 0

    @property
    def model_name(self) -> str:
        return "mock-llm"

    async def generate(self, question: str) -> str:
        self.__class__.call_count += 1
        print(f"  [LLM FALLBACK] question={question!r}")
        return f"[LLM answer to: {question}]"

    async def generate_with_context(
        self, question: str, context: list[tuple[str, str]]
    ) -> str:
        self.__class__.call_count += 1
        print(f"  [LLM RAG — {len(context)} context pair(s)] question={question!r}")
        return f"[RAG answer using {len(context)} pair(s) for: {question}]"


# ── Demo embedder (no HuggingFace model download needed) ──────────────────────


class DemoEmbedder:
    """
    Maps each unique query to a reproducible unit-norm 16-D vector via a
    seeded hash.  Avoids downloading a HuggingFace model for the demo.
    """

    _cache: dict[str, list[float]] = {}
    _DIM = 16

    @property
    def dim(self) -> int:
        return self._DIM

    async def embed_one(self, text: str) -> np.ndarray:
        import hashlib

        key = text.lower().strip()
        if key not in self._cache:
            seed = int(hashlib.md5(key.encode()).hexdigest(), 16) % (2**31)
            rng = np.random.default_rng(seed)
            v = rng.standard_normal(self._DIM).astype(np.float32)
            self._cache[key] = (v / np.linalg.norm(v)).tolist()
        return np.array(self._cache[key], dtype=np.float32)

    async def embed_many(self, texts: list[str]) -> list[np.ndarray]:
        return [await self.embed_one(t) for t in texts]


# ── Main demo ──────────────────────────────────────────────────────────────────


async def main() -> None:
    embedder_backend = os.getenv("EMBEDDER", "demo").lower()
    if embedder_backend == "hf":
        embedder = HuggingFaceEmbedder()
        vector_dim = embedder.dim
        print(f"  [demo] Embedder: HuggingFace ({embedder.dim}d)\n")
    else:
        embedder = DemoEmbedder()
        vector_dim = embedder.dim
        print("  [demo] Embedder: DemoEmbedder (set EMBEDDER=hf for semantic matching)\n")

    settings = Settings(
        REDIS_URL="redis://localhost:6379/0",
        KEY_PREFIX="demo_semcache",
        HIGH_TH=0.9,
        LOW_TH=0.7,
        TOP_K=3,
        DEFAULT_TTL=300,
        VECTOR_DIM=vector_dim,
    )

    redis_client = _make_redis_client(settings.redis_url)
    store = RedisStore(
        redis_url=settings.redis_url,
        key_prefix=settings.key_prefix,
        client=redis_client,
    )
    index = VectorIndex(dim=settings.vector_dim)
    cache = SemanticCache(
        settings=settings,
        embedder=embedder,
        store=store,
        index=index,
    )

    backend = os.getenv("LLM_BACKEND", "mock").lower()
    if backend == "groq":
        if not settings.groq_api_key:
            raise RuntimeError("LLM_BACKEND=groq requires GROQ_API_KEY to be set in .env")
        llm = GroqLLMCaller.from_settings(settings)
        print(f"  [demo] LLM backend: Groq ({settings.llm_model})\n")
    else:
        llm = MockLLM()
        print("  [demo] LLM backend: MockLLM (set LLM_BACKEND=groq to use Groq)\n")

    async with cache:
        print("=" * 60)
        print("SemanticCache Demo")
        print("=" * 60)

        queries = [
            ("What is Python?",                       "llm_fallback  — cold cache"),
            ("What is Python?",                       "direct_hit    — identical query"),
            ("Tell me about Python programming",      "rag/direct    — similar query"),
            ("What is Rust?",                         "llm_fallback  — new topic"),
            ("Explain the Rust programming language", "rag           — similar to above"),
        ]

        for question, expectation in queries:
            print(f"\n>>> {question!r}")
            print(f"    expected  : {expectation}")
            resp = await cache.query(question, llm)
            print(
                f"    strategy  : {resp.strategy}\n"
                f"    similarity: {resp.similarity}\n"
                f"    ctx_count : {resp.context_count}\n"
                f"    latency   : {resp.latency_ms:.1f} ms\n"
                f"    answer    : {resp.answer[:80]}"
            )

        # ── Interactive mode ───────────────────────────────────────────
        print(f"\n{'=' * 60}")
        print("Interactive mode — type a question, or 'quit'/'exit' to stop.")
        print("=" * 60)

        loop = asyncio.get_event_loop()
        while True:
            try:
                question = await loop.run_in_executor(None, lambda: input("\n? ").strip())
            except EOFError:
                break
            if not question:
                continue
            if question.lower() in {"quit", "exit"}:
                break
            resp = await cache.query(question, llm)
            print(
                f"    strategy  : {resp.strategy}\n"
                f"    similarity: {resp.similarity}\n"
                f"    ctx_count : {resp.context_count}\n"
                f"    latency   : {resp.latency_ms:.1f} ms\n"
                f"    answer    : {resp.answer[:120]}"
            )

        stats = await cache.stats()
        print(f"\n{'=' * 60}")
        print(f"Cache stats     : {stats}")
        if isinstance(llm, MockLLM):
            print(f"Total LLM calls : {MockLLM.call_count}  (lower = more cache hits)")
        print("=" * 60)

        await cache.flush()


if __name__ == "__main__":
    asyncio.run(main())
