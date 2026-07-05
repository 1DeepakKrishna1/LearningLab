"""Centralised, structured logging configuration."""
from __future__ import annotations

import logging
import sys
from logging.config import dictConfig


def configure_logging(level: str = "INFO") -> None:
    """Install a single, consistent logging configuration for the whole process."""
    dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "default": {
                    "format": "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
                    "datefmt": "%Y-%m-%dT%H:%M:%S%z",
                }
            },
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "stream": sys.stdout,
                    "formatter": "default",
                }
            },
            "root": {"handlers": ["console"], "level": level.upper()},
            "loggers": {
                # Quieten noisy third parties; surface our own at the configured level.
                "uvicorn.access": {"level": "WARNING"},
                "httpx": {"level": "WARNING"},
                "clawflow": {"level": level.upper()},
            },
        }
    )


def get_logger(name: str) -> logging.Logger:
    """Return a namespaced logger under the `clawflow.` root."""
    return logging.getLogger(f"clawflow.{name}")
