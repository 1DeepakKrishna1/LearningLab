"""Tests for the processing layer (cleaning, chunking, metadata extraction)."""

from __future__ import annotations

import pytest


class TestTextCleaner:
    def test_removes_control_characters(self) -> None:
        from src.processing.cleaner import TextCleaner
        cleaner = TextCleaner()
        dirty = "Hello\x00\x01World"
        clean = cleaner.clean(dirty)
        assert "\x00" not in clean
        assert "\x01" not in clean

    def test_fixes_soft_hyphenation(self) -> None:
        from src.processing.cleaner import TextCleaner
        cleaner = TextCleaner()
        hyphenated = "ma-\nchine learning"
        cleaned = cleaner.clean(hyphenated, fix_hyphenation=True)
        assert "machine" in cleaned

    def test_normalises_multiple_spaces(self) -> None:
        from src.processing.cleaner import TextCleaner
        cleaner = TextCleaner()
        text = "hello   world"
        cleaned = cleaner.clean(text)
        assert "  " not in cleaned

    def test_collapses_multiple_newlines(self) -> None:
        from src.processing.cleaner import TextCleaner
        cleaner = TextCleaner()
        text = "para1\n\n\n\n\npara2"
        cleaned = cleaner.clean(text)
        assert "\n\n\n" not in cleaned

    def test_clean_page_basic(self) -> None:
        from src.processing.cleaner import TextCleaner
        cleaner = TextCleaner()
        assert cleaner.clean_page("  hello  ") == "hello"


class TestSemanticChunker:
    def test_chunks_return_list_of_text_chunks(self, sample_text: str) -> None:
        from src.processing.chunker import SemanticChunker
        chunker = SemanticChunker(chunk_size=100, chunk_overlap=20, min_chunk_size=5)
        chunks = chunker.chunk(sample_text, "doc_001")
        assert len(chunks) >= 1

    def test_chunk_ids_are_unique(self, sample_text: str) -> None:
        from src.processing.chunker import SemanticChunker
        chunker = SemanticChunker(chunk_size=100, chunk_overlap=20, min_chunk_size=5)
        chunks = chunker.chunk(sample_text, "doc_001")
        ids = [c.chunk_id for c in chunks]
        assert len(ids) == len(set(ids))

    def test_chunk_references_correct_doc(self, sample_text: str) -> None:
        from src.processing.chunker import SemanticChunker
        chunker = SemanticChunker(chunk_size=100, chunk_overlap=20, min_chunk_size=5)
        chunks = chunker.chunk(sample_text, "doc_xyz")
        for chunk in chunks:
            assert chunk.doc_id == "doc_xyz"

    def test_sequence_is_monotonically_increasing(self, sample_text: str) -> None:
        from src.processing.chunker import SemanticChunker
        chunker = SemanticChunker(chunk_size=50, chunk_overlap=10, min_chunk_size=5)
        chunks = chunker.chunk(sample_text, "doc_001")
        seqs = [c.sequence for c in chunks]
        assert seqs == sorted(seqs)

    def test_fixed_strategy(self, sample_text: str) -> None:
        from src.processing.chunker import SemanticChunker
        chunker = SemanticChunker(strategy="fixed", chunk_size=50, chunk_overlap=10, min_chunk_size=5)
        chunks = chunker.chunk(sample_text, "doc_001")
        assert len(chunks) >= 1

    def test_sentence_strategy(self, sample_text: str) -> None:
        from src.processing.chunker import SemanticChunker
        chunker = SemanticChunker(strategy="sentence", chunk_size=100, chunk_overlap=10, min_chunk_size=5)
        chunks = chunker.chunk(sample_text, "doc_001")
        assert len(chunks) >= 1

    def test_min_chunk_size_filters_small_chunks(self) -> None:
        from src.processing.chunker import SemanticChunker
        chunker = SemanticChunker(chunk_size=100, chunk_overlap=0, min_chunk_size=1000)
        chunks = chunker.chunk("tiny text", "doc_001")
        assert chunks == []


class TestMetadataExtractor:
    def test_extract_returns_document_metadata(self, sample_text: str) -> None:
        from src.processing.metadata_extractor import MetadataExtractor
        from src.models.schemas import DocumentMetadata
        extractor = MetadataExtractor()
        meta = extractor.extract(sample_text, {"title": "Test Doc", "author": "Alice"}, total_pages=3)
        assert isinstance(meta, DocumentMetadata)
        assert meta.title == "Test Doc"
        assert meta.author == "Alice"
        assert meta.page_count == 3

    def test_infer_title_from_text(self) -> None:
        from src.processing.metadata_extractor import MetadataExtractor
        title = MetadataExtractor._infer_title("Introduction to Machine Learning\nsome content")
        assert title == "Introduction to Machine Learning"

    def test_word_count_is_positive(self, sample_text: str) -> None:
        from src.processing.metadata_extractor import MetadataExtractor
        extractor = MetadataExtractor()
        meta = extractor.extract(sample_text, {}, total_pages=1)
        assert meta.word_count > 0
