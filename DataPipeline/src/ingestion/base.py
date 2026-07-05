"""Abstract base ingester defining the contract for all source adapters."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Iterator

from src.models.schemas import DocumentSource, RawDocument
from src.ingestion.deduplicator import Deduplicator
from src.storage.file_store import FileStore
from src.utils.logger import get_logger
from src.utils.metrics import PipelineMetrics

logger = get_logger(__name__)


class BaseIngester(ABC):
    """Common ingestion scaffold: discover → hash → deduplicate → store raw."""

    def __init__(
        self,
        file_store: FileStore,
        deduplicator: Deduplicator,
        metrics: PipelineMetrics,
    ) -> None:
        self.store = file_store
        self.dedup = deduplicator
        self.metrics = metrics

    @abstractmethod
    def discover(self, **kwargs) -> Iterator[DocumentSource]:
        """Yield DocumentSource objects for every PDF found in the source."""
        ...

    def ingest(self, source: DocumentSource) -> RawDocument | None:
        """Download/copy the document locally, deduplicate, then store raw.

        Returns None if the document is a duplicate and should be skipped.
        """
        local_path = self._fetch_local(source)

        is_dup, content_hash = self.dedup.is_duplicate(local_path)
        if is_dup:
            existing_id = self.dedup.get_doc_id(content_hash)
            logger.info(
                "duplicate_skipped",
                file=source.file_name,
                existing_doc_id=existing_id,
            )
            return None

        doc_id = content_hash  # content-addressed ID
        raw_path = self.store.copy_raw(local_path, doc_id)
        self.dedup.register(content_hash, doc_id)
        self.metrics.record_ingestion(source.source_type.value)

        doc = RawDocument(
            doc_id=doc_id,
            source=source,
            local_path=str(raw_path),
            content_hash=content_hash,
        )
        self.store.save("raw", doc_id, doc)
        logger.info("document_ingested", doc_id=doc_id, file=source.file_name)
        return doc

    @abstractmethod
    def _fetch_local(self, source: DocumentSource) -> str:
        """Return local file system path to the document (download if needed)."""
        ...
