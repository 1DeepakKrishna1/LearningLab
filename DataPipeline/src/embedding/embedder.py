"""Embedding generation using sentence-transformers with batched inference."""

from __future__ import annotations

from typing import Any

import numpy as np

from src.models.schemas import EmbeddingRecord, TextChunk
from src.utils.logger import get_logger
from src.utils.metrics import PipelineMetrics

logger = get_logger(__name__)


class Embedder:
    """Generates embeddings for text chunks using sentence-transformers.

    The model is loaded once and reused across calls to amortise startup cost.
    """

    def __init__(
        self,
        model_name: str = "all-MiniLM-L6-v2",
        device: str = "cpu",
        batch_size: int = 64,
        normalize: bool = True,
        metrics: PipelineMetrics | None = None,
    ) -> None:
        self.model_name = model_name
        self.device = device
        self.batch_size = batch_size
        self.normalize = normalize
        self.metrics = metrics
        self._model: Any = None

    def _get_model(self):
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
            except ImportError as e:
                raise ImportError(
                    "sentence-transformers not installed. Run: pip install sentence-transformers"
                ) from e
            logger.info("loading_embedding_model", model=self.model_name, device=self.device)
            self._model = SentenceTransformer(self.model_name, device=self.device)
        return self._model

    @property
    def dimensions(self) -> int:
        model = self._get_model()
        return model.get_sentence_embedding_dimension()

    def embed_chunks(self, chunks: list[TextChunk]) -> list[EmbeddingRecord]:
        """Embed a list of TextChunk objects and return EmbeddingRecord objects."""
        if not chunks:
            return []

        model = self._get_model()
        texts = [chunk.text for chunk in chunks]

        logger.info("generating_embeddings", count=len(texts), model=self.model_name)

        embeddings = model.encode(
            texts,
            batch_size=self.batch_size,
            normalize_embeddings=self.normalize,
            show_progress_bar=False,
            convert_to_numpy=True,
        )

        records: list[EmbeddingRecord] = []
        for chunk, embedding in zip(chunks, embeddings):
            records.append(
                EmbeddingRecord(
                    chunk_id=chunk.chunk_id,
                    doc_id=chunk.doc_id,
                    embedding=embedding.tolist(),
                    model=self.model_name,
                    dimensions=len(embedding),
                )
            )

        if self.metrics:
            self.metrics.record_embeddings(len(records))

        logger.info("embeddings_generated", count=len(records))
        return records

    def embed_query(self, query: str) -> np.ndarray:
        """Embed a single query string for similarity search."""
        model = self._get_model()
        return model.encode([query], normalize_embeddings=self.normalize)[0]
