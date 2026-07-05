"""Tests for the embedding and vector store layers."""

from __future__ import annotations

import numpy as np
import pytest

from src.models.schemas import TextChunk


def make_chunks(doc_id: str = "doc_001", n: int = 3) -> list[TextChunk]:
    return [
        TextChunk(
            chunk_id=f"chunk_{i:04d}",
            doc_id=doc_id,
            sequence=i,
            text=f"This is sample chunk number {i} about machine learning and AI.",
        )
        for i in range(n)
    ]


class TestEmbedder:
    def test_embed_chunks_returns_records(self) -> None:
        from src.embedding.embedder import Embedder
        embedder = Embedder(model_name="all-MiniLM-L6-v2", device="cpu")
        chunks = make_chunks()
        records = embedder.embed_chunks(chunks)
        assert len(records) == len(chunks)

    def test_embedding_dimensions_match(self) -> None:
        from src.embedding.embedder import Embedder
        embedder = Embedder(model_name="all-MiniLM-L6-v2", device="cpu")
        chunks = make_chunks(n=2)
        records = embedder.embed_chunks(chunks)
        for record in records:
            assert record.dimensions == 384
            assert len(record.embedding) == 384

    def test_chunk_ids_are_preserved(self) -> None:
        from src.embedding.embedder import Embedder
        embedder = Embedder(model_name="all-MiniLM-L6-v2", device="cpu")
        chunks = make_chunks(n=2)
        records = embedder.embed_chunks(chunks)
        for chunk, record in zip(chunks, records):
            assert record.chunk_id == chunk.chunk_id

    def test_empty_input_returns_empty(self) -> None:
        from src.embedding.embedder import Embedder
        embedder = Embedder()
        assert embedder.embed_chunks([]) == []

    def test_embed_query_returns_numpy_array(self) -> None:
        from src.embedding.embedder import Embedder
        embedder = Embedder()
        vec = embedder.embed_query("what is machine learning?")
        assert isinstance(vec, np.ndarray)
        assert vec.shape == (384,)


class TestFAISSVectorStore:
    def test_add_and_search(self, tmp_dir) -> None:
        from src.embedding.embedder import Embedder
        from src.embedding.vector_store import FAISSVectorStore

        embedder = Embedder()
        chunks = make_chunks(n=5)
        records = embedder.embed_chunks(chunks)

        vs = FAISSVectorStore(save_path=str(tmp_dir / "vs"), dimensions=384)
        vs.add(records)

        assert vs.total_vectors == 5

        query = embedder.embed_query("machine learning")
        results = vs.search(query, top_k=3)
        assert len(results) == 3
        assert "chunk_id" in results[0]
        assert "distance" in results[0]

    def test_persistence(self, tmp_dir) -> None:
        from src.embedding.embedder import Embedder
        from src.embedding.vector_store import FAISSVectorStore

        embedder = Embedder()
        chunks = make_chunks(n=2)
        records = embedder.embed_chunks(chunks)

        path = str(tmp_dir / "vs_persist")
        vs1 = FAISSVectorStore(save_path=path, dimensions=384)
        vs1.add(records)

        vs2 = FAISSVectorStore(save_path=path, dimensions=384)
        assert vs2.total_vectors == 2

    def test_export_pinecone_format(self, tmp_dir) -> None:
        from src.embedding.embedder import Embedder
        from src.embedding.vector_store import FAISSVectorStore

        embedder = Embedder()
        chunks = make_chunks(n=1)
        records = embedder.embed_chunks(chunks)

        vs = FAISSVectorStore(save_path=str(tmp_dir / "vs"), dimensions=384)
        pinecone_format = vs.export_pinecone_format(records)
        assert len(pinecone_format) == 1
        assert "id" in pinecone_format[0]
        assert "values" in pinecone_format[0]
        assert "metadata" in pinecone_format[0]
