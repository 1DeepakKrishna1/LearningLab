"""Intelligent text chunking: semantic (preferred), fixed, and sentence strategies."""

from __future__ import annotations

import hashlib
import re
from typing import Literal

from src.models.schemas import TextChunk
from src.utils.logger import get_logger

logger = get_logger(__name__)

Strategy = Literal["semantic", "fixed", "sentence"]


class SemanticChunker:
    """Chunks text into overlapping windows using a configurable strategy.

    Semantic strategy uses paragraph boundaries as natural split points, then
    enforces max_tokens with overlap to preserve context across chunks.
    """

    def __init__(
        self,
        strategy: Strategy = "semantic",
        chunk_size: int = 512,
        chunk_overlap: int = 64,
        min_chunk_size: int = 50,
    ) -> None:
        self.strategy = strategy
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.min_chunk_size = min_chunk_size

    def chunk(self, text: str, doc_id: str) -> list[TextChunk]:
        """Split text into chunks and return a list of TextChunk objects."""
        if self.strategy == "semantic":
            raw_chunks = self._semantic_split(text)
        elif self.strategy == "sentence":
            raw_chunks = self._sentence_split(text)
        else:
            raw_chunks = self._fixed_split(text)

        # Filter out chunks that are too small
        raw_chunks = [c for c in raw_chunks if len(c.split()) >= self.min_chunk_size]

        chunks: list[TextChunk] = []
        for seq, chunk_text in enumerate(raw_chunks):
            chunk_id = self._make_chunk_id(doc_id, seq)
            chunks.append(
                TextChunk(
                    chunk_id=chunk_id,
                    doc_id=doc_id,
                    sequence=seq,
                    text=chunk_text.strip(),
                    token_count=len(chunk_text.split()),
                )
            )

        logger.debug("chunked", doc_id=doc_id, strategy=self.strategy, chunks=len(chunks))
        return chunks

    def _semantic_split(self, text: str) -> list[str]:
        """Split on paragraph boundaries, then merge small paragraphs and enforce max size."""
        paragraphs = re.split(r"\n\s*\n", text)
        return self._merge_and_window(paragraphs)

    def _sentence_split(self, text: str) -> list[str]:
        """Split on sentence boundaries using simple regex."""
        sentences = re.split(r"(?<=[.!?])\s+(?=[A-Z])", text)
        return self._merge_and_window(sentences)

    def _fixed_split(self, text: str) -> list[str]:
        """Fixed-size word-count windows with overlap."""
        words = text.split()
        chunks: list[str] = []
        i = 0
        while i < len(words):
            window = words[i : i + self.chunk_size]
            chunks.append(" ".join(window))
            i += self.chunk_size - self.chunk_overlap
        return chunks

    def _merge_and_window(self, segments: list[str]) -> list[str]:
        """Greedily merge segments into windows not exceeding chunk_size words."""
        chunks: list[str] = []
        current_words: list[str] = []
        overlap_words: list[str] = []

        for seg in segments:
            seg_words = seg.split()
            if not seg_words:
                continue

            if len(current_words) + len(seg_words) > self.chunk_size:
                if current_words:
                    chunks.append(" ".join(current_words))
                    overlap_words = current_words[-self.chunk_overlap :] if self.chunk_overlap else []
                current_words = overlap_words + seg_words
            else:
                current_words.extend(seg_words)

        if current_words:
            chunks.append(" ".join(current_words))

        return chunks

    @staticmethod
    def _make_chunk_id(doc_id: str, seq: int) -> str:
        raw = f"{doc_id}::chunk::{seq}"
        return hashlib.sha256(raw.encode()).hexdigest()[:16]
