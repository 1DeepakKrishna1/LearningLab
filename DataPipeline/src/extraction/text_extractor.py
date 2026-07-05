"""Text extraction from PDFs using PyMuPDF (primary) and pdfplumber (fallback)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from src.utils.logger import get_logger

logger = get_logger(__name__)


class TextExtractor:
    """Extracts structured per-page text from PDF files."""

    def __init__(self, backend: str = "pymupdf") -> None:
        self.backend = backend

    def extract(self, pdf_path: str) -> dict[str, Any]:
        """Return dict with 'raw_text', 'pages', 'total_pages', and 'pdf_metadata'."""
        if self.backend == "pymupdf":
            return self._extract_pymupdf(pdf_path)
        return self._extract_pdfplumber(pdf_path)

    def _extract_pymupdf(self, pdf_path: str) -> dict[str, Any]:
        try:
            import fitz  # PyMuPDF
        except ImportError as e:
            raise ImportError("PyMuPDF not installed. Run: pip install pymupdf") from e

        pages: list[dict[str, Any]] = []
        full_text_parts: list[str] = []

        with fitz.open(pdf_path) as doc:
            metadata = {
                "title": doc.metadata.get("title", ""),
                "author": doc.metadata.get("author", ""),
                "subject": doc.metadata.get("subject", ""),
                "keywords": doc.metadata.get("keywords", ""),
                "creator": doc.metadata.get("creator", ""),
                "producer": doc.metadata.get("producer", ""),
                "page_count": doc.page_count,
            }

            for page_num, page in enumerate(doc, start=1):
                # extract text blocks preserving layout
                blocks = page.get_text("dict", flags=fitz.TEXT_PRESERVE_LIGATURES)
                page_text = page.get_text("text")
                full_text_parts.append(page_text)

                pages.append(
                    {
                        "page": page_num,
                        "text": page_text,
                        "char_count": len(page_text),
                        "width": page.rect.width,
                        "height": page.rect.height,
                    }
                )

        return {
            "raw_text": "\n\n".join(full_text_parts),
            "pages": pages,
            "total_pages": len(pages),
            "pdf_metadata": metadata,
        }

    def _extract_pdfplumber(self, pdf_path: str) -> dict[str, Any]:
        try:
            import pdfplumber
        except ImportError as e:
            raise ImportError("pdfplumber not installed. Run: pip install pdfplumber") from e

        pages: list[dict[str, Any]] = []
        full_text_parts: list[str] = []

        with pdfplumber.open(pdf_path) as pdf:
            metadata = pdf.metadata or {}
            for page_num, page in enumerate(pdf.pages, start=1):
                text = page.extract_text() or ""
                full_text_parts.append(text)
                pages.append(
                    {
                        "page": page_num,
                        "text": text,
                        "char_count": len(text),
                        "width": page.width,
                        "height": page.height,
                    }
                )

        return {
            "raw_text": "\n\n".join(full_text_parts),
            "pages": pages,
            "total_pages": len(pages),
            "pdf_metadata": {k: str(v) for k, v in metadata.items()},
        }
