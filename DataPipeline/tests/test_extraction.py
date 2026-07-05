"""Tests for the PDF extraction layer."""

from __future__ import annotations

import pytest


class TestTextExtractor:
    def test_extract_text_returns_content(self, sample_pdf_path: str) -> None:
        from src.extraction.text_extractor import TextExtractor
        extractor = TextExtractor(backend="pymupdf")
        result = extractor.extract(sample_pdf_path)

        assert "raw_text" in result
        assert len(result["raw_text"]) > 10
        assert result["total_pages"] >= 1
        assert isinstance(result["pages"], list)

    def test_extract_pdfplumber_backend(self, sample_pdf_path: str) -> None:
        from src.extraction.text_extractor import TextExtractor
        extractor = TextExtractor(backend="pdfplumber")
        result = extractor.extract(sample_pdf_path)
        assert len(result["raw_text"]) > 0

    def test_pages_have_required_keys(self, sample_pdf_path: str) -> None:
        from src.extraction.text_extractor import TextExtractor
        extractor = TextExtractor()
        result = extractor.extract(sample_pdf_path)
        for page in result["pages"]:
            assert "page" in page
            assert "text" in page

    def test_pdf_metadata_extracted(self, sample_pdf_path: str) -> None:
        from src.extraction.text_extractor import TextExtractor
        extractor = TextExtractor()
        result = extractor.extract(sample_pdf_path)
        assert isinstance(result["pdf_metadata"], dict)
        assert "page_count" in result["pdf_metadata"]


class TestTableExtractor:
    def test_extract_returns_list(self, sample_pdf_path: str) -> None:
        from src.extraction.table_extractor import TableExtractor
        extractor = TableExtractor(backend="pdfplumber")
        tables = extractor.extract(sample_pdf_path)
        assert isinstance(tables, list)

    def test_no_crash_on_no_tables(self, sample_pdf_path: str) -> None:
        from src.extraction.table_extractor import TableExtractor
        extractor = TableExtractor()
        tables = extractor.extract(sample_pdf_path)
        # No tables in simple test doc — should return empty list without error
        assert isinstance(tables, list)

    def test_markdown_conversion(self) -> None:
        from src.extraction.table_extractor import TableExtractor
        headers = ["Col A", "Col B"]
        rows = [["1", "2"], ["3", "4"]]
        md = TableExtractor._to_markdown(headers, rows)
        assert "Col A" in md
        assert "---" in md


class TestImageExtractor:
    def test_extract_returns_list(self, tmp_dir, sample_pdf_path: str) -> None:
        from src.extraction.image_extractor import ImageExtractor
        extractor = ImageExtractor(output_dir=str(tmp_dir), ocr_enabled=False)
        images = extractor.extract(sample_pdf_path, "test_doc")
        assert isinstance(images, list)


class TestPDFProcessor:
    def test_process_returns_extracted_content(self, tmp_dir, sample_pdf_path: str) -> None:
        from src.extraction.pdf_processor import PDFProcessor
        from src.models.schemas import ExtractedContent
        processor = PDFProcessor(output_dir=str(tmp_dir), ocr_enabled=False)
        result = processor.process(sample_pdf_path, "doc001", "test.pdf")

        assert isinstance(result, ExtractedContent)
        assert result.doc_id == "doc001"
        assert result.total_pages >= 1
        assert len(result.raw_text) > 0
