"""Local filesystem ingester with glob-based discovery and mtime tracking."""

from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from typing import Iterator

from src.ingestion.base import BaseIngester
from src.ingestion.deduplicator import Deduplicator
from src.models.schemas import DocumentSource, SourceType
from src.storage.file_store import FileStore
from src.utils.logger import get_logger
from src.utils.metrics import PipelineMetrics

logger = get_logger(__name__)


class LocalIngester(BaseIngester):
    """Ingest PDFs from a local directory tree."""

    def __init__(
        self,
        input_dir: str,
        file_store: FileStore,
        deduplicator: Deduplicator,
        metrics: PipelineMetrics,
        extensions: tuple[str, ...] = (".pdf",),
    ) -> None:
        super().__init__(file_store, deduplicator, metrics)
        self.input_dir = Path(input_dir)
        self.extensions = extensions

    def discover(self, **kwargs) -> Iterator[DocumentSource]:
        """Recursively yield DocumentSource for every matching file."""
        if not self.input_dir.exists():
            logger.warning("input_dir_not_found", path=str(self.input_dir))
            return

        for root, _dirs, files in os.walk(self.input_dir):
            for fname in sorted(files):
                fpath = Path(root) / fname
                if fpath.suffix.lower() not in self.extensions:
                    continue

                stat = fpath.stat()
                yield DocumentSource(
                    source_type=SourceType.LOCAL,
                    source_path=str(fpath),
                    file_name=fname,
                    file_size_bytes=stat.st_size,
                    last_modified=datetime.fromtimestamp(stat.st_mtime),
                )

    def _fetch_local(self, source: DocumentSource) -> str:
        return source.source_path
