"""Tests for the ingestion layer."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from src.ingestion.deduplicator import Deduplicator
from src.ingestion.local import LocalIngester
from src.models.schemas import SourceType


class TestDeduplicator:
    def test_hash_file_returns_hex_string(self, sample_pdf_path: str) -> None:
        dedup = Deduplicator.__new__(Deduplicator)
        dedup._index = {}
        dedup._path = Path("/dev/null")
        h = Deduplicator.hash_file(sample_pdf_path)
        assert isinstance(h, str) and len(h) == 64

    def test_is_not_duplicate_initially(self, deduplicator: Deduplicator, sample_pdf_path: str) -> None:
        is_dup, h = deduplicator.is_duplicate(sample_pdf_path)
        assert not is_dup
        assert len(h) == 64

    def test_is_duplicate_after_register(self, deduplicator: Deduplicator, sample_pdf_path: str) -> None:
        _, h = deduplicator.is_duplicate(sample_pdf_path)
        deduplicator.register(h, "test_doc_001")
        is_dup, _ = deduplicator.is_duplicate(sample_pdf_path)
        assert is_dup

    def test_get_doc_id(self, deduplicator: Deduplicator, sample_pdf_path: str) -> None:
        _, h = deduplicator.is_duplicate(sample_pdf_path)
        deduplicator.register(h, "doc_abc")
        assert deduplicator.get_doc_id(h) == "doc_abc"

    def test_persistence(self, tmp_dir: Path, sample_pdf_path: str) -> None:
        state_path = str(tmp_dir / "dedup.json")
        d1 = Deduplicator(state_path)
        _, h = d1.is_duplicate(sample_pdf_path)
        d1.register(h, "persistent_doc")

        d2 = Deduplicator(state_path)
        assert d2.get_doc_id(h) == "persistent_doc"


class TestLocalIngester:
    def test_discover_finds_pdfs(
        self, tmp_dir: Path, sample_pdf_path: str, file_store, deduplicator, metrics
    ) -> None:
        pdf_dir = tmp_dir / "pdfs"
        pdf_dir.mkdir()
        shutil.copy(sample_pdf_path, pdf_dir / "test.pdf")

        ingester = LocalIngester(str(pdf_dir), file_store, deduplicator, metrics)
        sources = list(ingester.discover())
        assert len(sources) == 1
        assert sources[0].file_name == "test.pdf"
        assert sources[0].source_type == SourceType.LOCAL

    def test_discover_ignores_non_pdf(
        self, tmp_dir: Path, file_store, deduplicator, metrics
    ) -> None:
        pdf_dir = tmp_dir / "pdfs"
        pdf_dir.mkdir()
        (pdf_dir / "readme.txt").write_text("not a pdf")

        ingester = LocalIngester(str(pdf_dir), file_store, deduplicator, metrics)
        sources = list(ingester.discover())
        assert len(sources) == 0

    def test_ingest_returns_raw_document(
        self, tmp_dir: Path, sample_pdf_path: str, file_store, deduplicator, metrics
    ) -> None:
        pdf_dir = tmp_dir / "pdfs"
        pdf_dir.mkdir()
        shutil.copy(sample_pdf_path, pdf_dir / "test.pdf")

        ingester = LocalIngester(str(pdf_dir), file_store, deduplicator, metrics)
        sources = list(ingester.discover())
        raw = ingester.ingest(sources[0])

        assert raw is not None
        assert len(raw.doc_id) == 64
        assert raw.source.source_type == SourceType.LOCAL

    def test_ingest_deduplicates(
        self, tmp_dir: Path, sample_pdf_path: str, file_store, deduplicator, metrics
    ) -> None:
        pdf_dir = tmp_dir / "pdfs"
        pdf_dir.mkdir()
        shutil.copy(sample_pdf_path, pdf_dir / "test.pdf")

        ingester = LocalIngester(str(pdf_dir), file_store, deduplicator, metrics)
        sources = list(ingester.discover())

        first = ingester.ingest(sources[0])
        second = ingester.ingest(sources[0])

        assert first is not None
        assert second is None  # duplicate

    def test_discover_empty_dir_returns_empty(
        self, tmp_dir: Path, file_store, deduplicator, metrics
    ) -> None:
        empty_dir = tmp_dir / "empty"
        empty_dir.mkdir()
        ingester = LocalIngester(str(empty_dir), file_store, deduplicator, metrics)
        assert list(ingester.discover()) == []
