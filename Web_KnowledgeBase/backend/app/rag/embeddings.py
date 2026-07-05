"""OpenAI embeddings, returned as L2-normalized float32 vectors for FAISS."""
from __future__ import annotations

import threading

import numpy as np
from tenacity import retry, stop_after_attempt, wait_exponential

from ..config import get_settings

_client = None
_lock = threading.Lock()
_dim_cache: dict[str, int] = {}


def _get_client():
    global _client
    if _client is None:
        with _lock:
            if _client is None:
                from openai import OpenAI

                settings = get_settings()
                _client = OpenAI(
                    api_key=settings.openai_api_key,
                    base_url=settings.openai_base_url,
                )
    return _client


@retry(stop=stop_after_attempt(4), wait=wait_exponential(min=1, max=20))
def _embed_batch(texts: list[str], model_name: str) -> list[list[float]]:
    # OpenAI rejects empty strings; substitute a single space.
    cleaned = [t if t.strip() else " " for t in texts]
    resp = _get_client().embeddings.create(model=model_name, input=cleaned)
    return [d.embedding for d in resp.data]


def embed(texts: list[str], model_name: str, *, batch_size: int = 128) -> np.ndarray:
    """Return L2-normalized float32 embeddings (cosine == inner product)."""
    if not texts:
        return np.zeros((0, dimension(model_name)), dtype="float32")

    vectors: list[list[float]] = []
    for i in range(0, len(texts), batch_size):
        vectors.extend(_embed_batch(texts[i : i + batch_size], model_name))

    arr = np.asarray(vectors, dtype="float32")
    norms = np.linalg.norm(arr, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    normalized = arr / norms
    _dim_cache[model_name] = normalized.shape[1]
    return normalized


def embed_one(text: str, model_name: str) -> np.ndarray:
    return embed([text], model_name)[0]


def dimension(model_name: str) -> int:
    if model_name not in _dim_cache:
        vec = _embed_batch(["dimension probe"], model_name)[0]
        _dim_cache[model_name] = len(vec)
    return _dim_cache[model_name]
