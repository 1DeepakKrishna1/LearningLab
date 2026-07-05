"""Image extraction, OCR, and optional captioning from PDF pages."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Optional

from src.models.schemas import ImageData
from src.utils.logger import get_logger

logger = get_logger(__name__)


class ImageExtractor:
    """Extracts embedded images from PDFs, runs OCR, and optionally generates captions."""

    def __init__(
        self,
        output_dir: str,
        ocr_enabled: bool = True,
        ocr_backend: str = "easyocr",
        ocr_languages: list[str] = None,
        min_size: int = 100,
    ) -> None:
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.ocr_enabled = ocr_enabled
        self.ocr_backend = ocr_backend
        self.ocr_languages = ocr_languages or ["en"]
        self.min_size = min_size
        self._ocr_reader: Any = None

    def _get_ocr_reader(self):
        if self._ocr_reader is not None:
            return self._ocr_reader
        if self.ocr_backend == "easyocr":
            try:
                import easyocr
                self._ocr_reader = easyocr.Reader(self.ocr_languages, gpu=False)
            except ImportError as e:
                raise ImportError("easyocr not installed. Run: pip install easyocr") from e
        return self._ocr_reader

    def extract(self, pdf_path: str, doc_id: str) -> list[ImageData]:
        """Extract all images from the PDF, save them, and run OCR."""
        try:
            import fitz
        except ImportError as e:
            raise ImportError("PyMuPDF not installed.") from e

        results: list[ImageData] = []
        img_dir = self.output_dir / doc_id
        img_dir.mkdir(exist_ok=True)

        with fitz.open(pdf_path) as doc:
            for page_num, page in enumerate(doc, start=1):
                img_list = page.get_images(full=True)
                for img_idx, img_ref in enumerate(img_list):
                    xref = img_ref[0]
                    base_image = doc.extract_image(xref)
                    img_bytes = base_image["image"]
                    img_ext = base_image["ext"]
                    width = base_image["width"]
                    height = base_image["height"]

                    if width < self.min_size or height < self.min_size:
                        continue

                    img_filename = f"p{page_num}_img{img_idx}.{img_ext}"
                    img_path = img_dir / img_filename
                    img_path.write_bytes(img_bytes)

                    ocr_text: Optional[str] = None
                    if self.ocr_enabled:
                        ocr_text = self._run_ocr(str(img_path))

                    results.append(
                        ImageData(
                            page=page_num,
                            index=img_idx,
                            width=width,
                            height=height,
                            format=img_ext,
                            local_path=str(img_path),
                            ocr_text=ocr_text,
                        )
                    )

        logger.info("images_extracted", doc_id=doc_id, count=len(results))
        return results

    def _run_ocr(self, image_path: str) -> Optional[str]:
        try:
            reader = self._get_ocr_reader()
            if reader is None:
                return None
            results = reader.readtext(image_path, detail=0, paragraph=True)
            return " ".join(results).strip() or None
        except Exception as exc:
            logger.warning("ocr_failed", path=image_path, error=str(exc))
            return None
