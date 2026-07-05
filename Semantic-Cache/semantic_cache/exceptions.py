"""Domain exception hierarchy for SemanticCache."""


class SemanticCacheError(Exception):
    """Base exception for all semantic cache errors."""


class EmbeddingError(SemanticCacheError):
    """Raised when an embedding call fails."""


class RedisConnectionError(SemanticCacheError):
    """Raised when Redis is unreachable or returns an unexpected error."""


class VectorDimensionMismatch(SemanticCacheError):
    """Raised when a stored or computed embedding dim differs from config."""

    def __init__(self, expected: int, actual: int) -> None:
        super().__init__(
            f"Vector dimension mismatch: expected {expected}, got {actual}. "
            "Ensure VECTOR_DIM in config matches the embedding provider output."
        )
        self.expected = expected
        self.actual = actual


class CacheCorruptionError(SemanticCacheError):
    """Raised when a Redis entry cannot be deserialised into a valid CacheEntry."""
