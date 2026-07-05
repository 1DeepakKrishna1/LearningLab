"""
SemanticCache — production-quality semantic cache with:

* Vector similarity via numpy cosine (no FAISS)
* HuggingFace embeddings (local, no external API)
* Groq LLM for generation (ultra-fast inference)
* Metadata + TTL in Redis (native EXPIRE)
* No stale index: keyspace notifications + validation-on-read
* Hybrid strategy: direct hit → RAG generation → LLM fallback

Quick start::

    import asyncio
    from semantic_cache import GroqLLMCaller, SemanticCache, Settings

    async def main():
        settings = Settings()   # reads from .env / environment
        llm = GroqLLMCaller.from_settings(settings)

        async with SemanticCache.create(settings) as cache:
            resp = await cache.query("What is Python?", llm)
            print(resp.strategy, resp.answer)

    asyncio.run(main())
"""

from semantic_cache.cache import GroqLLMCaller, SemanticCache
from semantic_cache.config import Settings
from semantic_cache.embedders import (
    EmbedderProtocol,
    HuggingFaceEmbedder,
    build_embedder,
)
from semantic_cache.exceptions import (
    CacheCorruptionError,
    EmbeddingError,
    RedisConnectionError,
    SemanticCacheError,
    VectorDimensionMismatch,
)
from semantic_cache.store.schemas import CacheEntry, CacheResponse, SearchResult

__all__ = [
    # Core
    "SemanticCache",
    "Settings",
    # LLM
    "GroqLLMCaller",
    # Embeddings
    "EmbedderProtocol",
    "HuggingFaceEmbedder",
    "build_embedder",
    # Schemas
    "CacheEntry",
    "CacheResponse",
    "SearchResult",
    # Exceptions
    "SemanticCacheError",
    "EmbeddingError",
    "RedisConnectionError",
    "VectorDimensionMismatch",
    "CacheCorruptionError",
]
