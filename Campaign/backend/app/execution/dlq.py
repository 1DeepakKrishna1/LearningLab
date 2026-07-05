"""Dead-letter handling and retry policy.

The DLQ is a JSONL file under ``data/`` (self-hosted, no broker). Failed
deliveries that exhaust retries are appended here for inspection/replay.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

from app.core.config import settings

logger = logging.getLogger("app.execution.dlq")
_DLQ_PATH = settings.DATA_DIR / "dead_letter.jsonl"


def dead_letter(delivery_id: int, campaign_id: int, contact_id: int, error: str) -> None:
    record = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "delivery_id": delivery_id,
        "campaign_id": campaign_id,
        "contact_id": contact_id,
        "error": error,
    }
    try:
        _DLQ_PATH.parent.mkdir(parents=True, exist_ok=True)
        with _DLQ_PATH.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record) + "\n")
    except OSError as exc:  # pragma: no cover
        logger.error("Failed to write DLQ entry: %s", exc)
    logger.warning("Dead-lettered delivery %s (campaign %s): %s", delivery_id, campaign_id, error)
