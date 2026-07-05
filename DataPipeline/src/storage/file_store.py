"""Phase-wise file storage with traceability and idempotency support."""

from __future__ import annotations

import json
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from src.utils.logger import get_logger

logger = get_logger(__name__)

PHASE_DIRS = {
    "raw": "raw",
    "extracted": "extracted",
    "processed": "processed",
    "embeddings": "embeddings",
    "knowledge_graph": "knowledge_graph",
    "faq": "faq",
    "questions": "questions",
}


class FileStore:
    """Manages structured output directory and JSON persistence for all pipeline phases."""

    def __init__(self, base_output_dir: str = "./output") -> None:
        self.base = Path(base_output_dir)
        self._ensure_dirs()
        self._state_file = self.base / ".pipeline_state.json"
        self._state: dict[str, Any] = self._load_state()

    def _ensure_dirs(self) -> None:
        for phase in PHASE_DIRS.values():
            (self.base / phase).mkdir(parents=True, exist_ok=True)

    def _load_state(self) -> dict[str, Any]:
        if self._state_file.exists():
            with self._state_file.open("r", encoding="utf-8") as f:
                return json.load(f)
        return {}

    def _save_state(self) -> None:
        with self._state_file.open("w", encoding="utf-8") as f:
            json.dump(self._state, f, indent=2, default=str)

    # ── Public API ─────────────────────────────────────────────────────────────

    def save(self, phase: str, doc_id: str, data: Any, suffix: str = "") -> Path:
        """Serialise data to JSON in the appropriate phase directory."""
        if phase not in PHASE_DIRS:
            raise ValueError(f"Unknown phase '{phase}'. Valid: {list(PHASE_DIRS)}")

        phase_dir = self.base / PHASE_DIRS[phase]
        fname = f"{doc_id}{('_' + suffix) if suffix else ''}.json"
        dest = phase_dir / fname

        payload: Any
        if hasattr(data, "model_dump"):
            payload = data.model_dump(mode="json")
        elif isinstance(data, list) and data and hasattr(data[0], "model_dump"):
            payload = [item.model_dump(mode="json") for item in data]
        else:
            payload = data

        with dest.open("w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, default=str, ensure_ascii=False)

        self._update_doc_state(doc_id, phase, str(dest))
        logger.debug("file_saved", phase=phase, doc_id=doc_id, path=str(dest))
        return dest

    def load(self, phase: str, doc_id: str, suffix: str = "") -> Optional[Any]:
        """Load JSON data for a given phase and document ID."""
        phase_dir = self.base / PHASE_DIRS[phase]
        fname = f"{doc_id}{('_' + suffix) if suffix else ''}.json"
        dest = phase_dir / fname
        if not dest.exists():
            return None
        with dest.open("r", encoding="utf-8") as f:
            return json.load(f)

    def exists(self, phase: str, doc_id: str, suffix: str = "") -> bool:
        """Check if output already exists for a given phase (idempotency check)."""
        phase_dir = self.base / PHASE_DIRS[phase]
        fname = f"{doc_id}{('_' + suffix) if suffix else ''}.json"
        return (phase_dir / fname).exists()

    def copy_raw(self, source_path: str, doc_id: str) -> Path:
        """Copy the original PDF into the raw directory for traceability."""
        src = Path(source_path)
        dest = self.base / "raw" / f"{doc_id}{src.suffix}"
        if not dest.exists():
            shutil.copy2(str(src), str(dest))
            logger.info("raw_document_stored", doc_id=doc_id, dest=str(dest))
        return dest

    def get_doc_state(self, doc_id: str) -> dict[str, Any]:
        return self._state.get(doc_id, {})

    def is_completed(self, doc_id: str) -> bool:
        return self._state.get(doc_id, {}).get("status") == "completed"

    def mark_completed(self, doc_id: str) -> None:
        self._update_doc_state(doc_id, "status", "completed")

    def mark_failed(self, doc_id: str, error: str) -> None:
        state = self._state.setdefault(doc_id, {})
        state["status"] = "failed"
        state.setdefault("errors", []).append({"time": datetime.utcnow().isoformat(), "error": error})
        self._save_state()

    def _update_doc_state(self, doc_id: str, key: str, value: Any) -> None:
        state = self._state.setdefault(doc_id, {})
        state[key] = value
        state["updated_at"] = datetime.utcnow().isoformat()
        self._save_state()

    def list_completed(self) -> list[str]:
        return [did for did, s in self._state.items() if s.get("status") == "completed"]

    def list_failed(self) -> list[str]:
        return [did for did, s in self._state.items() if s.get("status") == "failed"]
