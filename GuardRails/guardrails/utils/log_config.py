"""Structured JSON logging configuration with correlation-ID support."""
from __future__ import annotations

import json
import logging
import logging.handlers
import sys
import traceback
from datetime import datetime, timezone
from typing import Any, Dict, Optional

_RESERVED_ATTRS = frozenset(logging.LogRecord.__dict__.keys())


class StructuredFormatter(logging.Formatter):
    """Emits each log record as a single JSON line."""

    def format(self, record: logging.LogRecord) -> str:
        payload: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Attach any extra fields (e.g. correlation_id, guardrail)
        for key, value in record.__dict__.items():
            if key not in _RESERVED_ATTRS and not key.startswith("_"):
                payload[key] = value

        if record.exc_info:
            payload["exception"] = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else None,
                "message": str(record.exc_info[1]),
                "traceback": traceback.format_exception(*record.exc_info),
            }

        return json.dumps(payload, default=str)


def setup_logging(
    level: str = "INFO",
    structured: bool = True,
    log_file: Optional[str] = None,
) -> None:
    """Configure the 'guardrails' logger hierarchy."""
    root = logging.getLogger("guardrails")
    root.setLevel(getattr(logging, level.upper(), logging.INFO))
    root.handlers.clear()
    root.propagate = False

    stream_handler: logging.Handler = logging.StreamHandler(sys.stdout)
    if structured:
        stream_handler.setFormatter(StructuredFormatter())
    else:
        stream_handler.setFormatter(
            logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
        )
    root.addHandler(stream_handler)

    if log_file:
        file_handler = logging.handlers.RotatingFileHandler(
            log_file, maxBytes=10 * 1024 * 1024, backupCount=5
        )
        file_handler.setFormatter(StructuredFormatter())
        root.addHandler(file_handler)
