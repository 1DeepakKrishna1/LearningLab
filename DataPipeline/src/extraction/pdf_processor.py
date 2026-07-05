"""Composite PDF processor: orchestrates text, table, and image extraction."""

from __future__ import annotations

from src.extraction.image_extractor import ImageExtractor
from src.extraction.table_extractor import TableExtractor
from src.extraction.text_extractor import TextExtractor
from src.models.schemas import ExtractedContent
from src.utils.logger import get_logger
from src.utils.metrics import PipelineMetrics

logger = get_logger(__name__)


class PDFProcessor:
    """Single entry-point that runs all extractors and returns ExtractedContent."""

    def __init__(
        self,
        output_dir: str = "./output",
        text_backend: str = "pymupdf",
        table_backend: str = "pdfplumber",
        ocr_enabled: bool = True,
        ocr_backend: str = "easyocr",
        ocr_languages: list[str] = None,
        metrics: PipelineMetrics | None = None,
    ) -> None:
        self.text_extractor = TextExtractor(backend=text_backend)
        self.table_extractor = TableExtractor(backend=table_backend)
        self.image_extractor = ImageExtractor(
            output_dir=f"{output_dir}/images",
            ocr_enabled=ocr_enabled,
            ocr_backend=ocr_backend,
            ocr_languages=ocr_languages or ["en"],
        )
        self.metrics = metrics

    def process(self, pdf_path: str, doc_id: str, file_name: str) -> ExtractedContent:
        """Run full extraction pipeline and return a validated ExtractedContent."""
        logger.info("extraction_started", doc_id=doc_id, file=file_name)

        stage = self.metrics.time_stage("extraction") if self.metrics else _nullcontext()

        with stage:
            text_data = self.text_extractor.extract(pdf_path)
            tables = self.table_extractor.extract(pdf_path)
            images = self.image_extractor.extract(pdf_path, doc_id)

        content = ExtractedContent(
            doc_id=doc_id,
            file_name=file_name,
            total_pages=text_data["total_pages"],
            raw_text=text_data["raw_text"],
            pages=text_data["pages"],
            tables=tables,
            images=images,
            pdf_metadata=text_data["pdf_metadata"],
        )

        logger.info(
            "extraction_completed",
            doc_id=doc_id,
            pages=content.total_pages,
            tables=len(tables),
            images=len(images),
            chars=len(content.raw_text),
        )
        return content


class _nullcontext:
    """Minimal no-op context manager for when metrics is None."""
    def __enter__(self): return self
    def __exit__(self, *_): pass
