"""Hash-based deduplication for ingested documents."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Optional

from src.utils.logger import get_logger

logger = get_logger(__name__)


class Deduplicator:
    """Tracks seen content hashes to prevent reprocessing identical documents."""

    def __init__(self, state_path: str = "./output/.dedup_index.json") -> None:
        self._path = Path(state_path)
        self._index: dict[str, str] = self._load()

    def _load(self) -> dict[str, str]:
        if self._path.exists():
            with self._path.open("r", encoding="utf-8") as f:
                return json.load(f)
        return {}

    def _save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with self._path.open("w", encoding="utf-8") as f:
            json.dump(self._index, f, indent=2)

    @staticmethod
    def hash_file(file_path: str, algorithm: str = "sha256") -> str:
        """Return hex digest of file contents using the specified algorithm."""
        h = hashlib.new(algorithm)
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()

    def is_duplicate(self, file_path: str) -> tuple[bool, str]:
        """Return (is_duplicate, content_hash). Does NOT register the hash."""
        content_hash = self.hash_file(file_path)
        return content_hash in self._index, content_hash

    def register(self, content_hash: str, doc_id: str) -> None:
        """Register a hash → doc_id mapping after successful ingestion."""
        self._index[content_hash] = doc_id
        self._save()
        logger.debug("hash_registered", doc_id=doc_id, hash_prefix=content_hash[:8])

    def get_doc_id(self, content_hash: str) -> Optional[str]:
        return self._index.get(content_hash)

    def __len__(self) -> int:
        return len(self._index)
