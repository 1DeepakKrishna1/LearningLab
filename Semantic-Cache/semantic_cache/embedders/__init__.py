"""
Embedding provider for SemanticCache.

``HuggingFaceEmbedder`` implements ``EmbedderProtocol`` (structural duck typing
via ``typing.Protocol``).  No concrete class needs to import the protocol.

Unit-norm guarantee
───────────────────
The provider returns L2-normalised float32 vectors, allowing the vector index
to use a plain dot product as cosine similarity — no division at search time.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Protocol, runtime_checkable

import numpy as np

logger = logging.getLogger(__name__)

_EPSILON = 1e-10


def _l2_normalise(v: np.ndarray) -> np.ndarray:
    norm = np.linalg.norm(v, axis=-1, keepdims=True)
    return v / np.where(norm == 0, 1.0, norm)


# ── Protocol ───────────────────────────────────────────────────────────────────


@runtime_checkable
class EmbedderProtocol(Protocol):
    async def embed_one(self, text: str) -> np.ndarray: ...
    async def embed_many(self, texts: list[str]) -> list[np.ndarray]: ...

    @property
    def dim(self) -> int: ...


# ── HuggingFace Embedder ───────────────────────────────────────────────────────


class HuggingFaceEmbedder:
    """
    Synchronous HuggingFace model wrapped for async use via run_in_executor.

    Uses mean-pooling of the last hidden state followed by L2 normalisation.
    Model is loaded once at construction and kept in memory.
    """

    def __init__(
        self,
        model_name: str = "sentence-transformers/all-MiniLM-L6-v2",
        device: str | None = None,
    ) -> None:
        import torch
        from transformers import AutoModel, AutoTokenizer

        self._tokenizer = AutoTokenizer.from_pretrained(model_name)
        self._model = AutoModel.from_pretrained(model_name)
        self._device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self._model.to(self._device)
        self._model.eval()

        # Infer dimension from a dummy forward pass
        import torch

        with torch.no_grad():
            dummy = self._tokenizer(
                "hello", return_tensors="pt", padding=True, truncation=True
            )
            dummy = {k: v.to(self._device) for k, v in dummy.items()}
            out = self._model(**dummy)
        self._dim = int(out.last_hidden_state.shape[-1])
        logger.info(
            "HuggingFaceEmbedder loaded '%s' on %s (dim=%d).",
            model_name,
            self._device,
            self._dim,
        )

    @property
    def dim(self) -> int:
        return self._dim

    async def embed_one(self, text: str) -> np.ndarray:
        results = await self.embed_many([text])
        return results[0]

    async def embed_many(self, texts: list[str]) -> list[np.ndarray]:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._encode_sync, texts)

    def _encode_sync(self, texts: list[str]) -> list[np.ndarray]:
        import torch

        encoded = self._tokenizer(
            texts,
            padding=True,
            truncation=True,
            max_length=512,
            return_tensors="pt",
        )
        encoded = {k: v.to(self._device) for k, v in encoded.items()}

        with torch.no_grad():
            output = self._model(**encoded)

        # Mean-pool over token dimension, respecting attention mask
        mask = encoded["attention_mask"].unsqueeze(-1).float()
        summed = (output.last_hidden_state * mask).sum(dim=1)
        count = mask.sum(dim=1).clamp(min=_EPSILON)
        mean_pooled = (summed / count).cpu().numpy().astype(np.float32)

        normed = _l2_normalise(mean_pooled)
        return [normed[i] for i in range(normed.shape[0])]


# ── Factory ────────────────────────────────────────────────────────────────────


def build_embedder(settings: "Settings") -> EmbedderProtocol:  # noqa: F821
    """Instantiate the HuggingFace embedding provider from settings."""
    return HuggingFaceEmbedder(model_name=settings.hf_model_name)


__all__ = [
    "EmbedderProtocol",
    "HuggingFaceEmbedder",
    "build_embedder",
]
