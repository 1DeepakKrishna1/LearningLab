"""Dual-sink conversation logger: file + SQLite."""
from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path

from app.config import LOGS_DIR

# File logger setup
_log_file = LOGS_DIR / "conversations.log"
_file_handler = logging.FileHandler(_log_file, encoding="utf-8")
_file_handler.setFormatter(
    logging.Formatter("%(asctime)s %(levelname)s %(message)s", datefmt="%Y-%m-%dT%H:%M:%S")
)

_logger = logging.getLogger("conversations")
_logger.setLevel(logging.INFO)
if not _logger.handlers:
    _logger.addHandler(_file_handler)


def log_message(
    *,
    event: str,
    conversation_id: str,
    username: str,
    role: str,
    content: str,
    tokens_in: int = 0,
    tokens_out: int = 0,
    time_taken: float = 0.0,
    guardrail_triggered: bool = False,
    extra: dict | None = None,
) -> None:
    record = {
        "event": event,
        "conversation_id": conversation_id,
        "username": username,
        "role": role,
        "content": content[:500],  # truncate for log readability
        "tokens_in": tokens_in,
        "tokens_out": tokens_out,
        "time_taken": time_taken,
        "guardrail_triggered": guardrail_triggered,
        "ts": datetime.utcnow().isoformat(),
    }
    if extra:
        record.update(extra)
    _logger.info(json.dumps(record, ensure_ascii=False))
