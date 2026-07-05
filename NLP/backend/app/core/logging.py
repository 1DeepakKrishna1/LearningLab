"""
Structured JSON logging via loguru.
Includes a middleware that stamps each request with a unique request_id.
"""
from __future__ import annotations

import sys
import time
import uuid
from typing import Callable

from fastapi import Request, Response
from loguru import logger
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import get_settings

settings = get_settings()

_CONFIGURED = False


def configure_logging() -> None:
    """Configure loguru once at startup."""
    global _CONFIGURED
    if _CONFIGURED:
        return
    _CONFIGURED = True

    logger.remove()

    # Console — human-readable in debug, JSON in production
    if settings.debug:
        logger.add(
            sys.stderr,
            level=settings.log_level,
            format=(
                "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
                "<level>{level: <8}</level> | "
                "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
                "<level>{message}</level>"
            ),
            colorize=True,
            backtrace=True,
            diagnose=True,
        )
    else:
        logger.add(
            sys.stderr,
            level=settings.log_level,
            serialize=True,  # JSON lines
            backtrace=False,
            diagnose=False,
        )

    # File sink (always JSON)
    import os

    os.makedirs(os.path.dirname(settings.log_file), exist_ok=True)
    logger.add(
        settings.log_file,
        level=settings.log_level,
        rotation="50 MB",
        retention="14 days",
        compression="gz",
        serialize=True,
        enqueue=True,  # thread-safe async
    )


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Attach request_id to every request and log summary on completion."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        request_id = str(uuid.uuid4())
        start = time.perf_counter()

        with logger.contextualize(request_id=request_id):
            logger.info(
                "request_started",
                method=request.method,
                path=request.url.path,
                query=str(request.query_params),
            )

            try:
                response: Response = await call_next(request)
            except Exception as exc:
                elapsed = (time.perf_counter() - start) * 1000
                logger.error(
                    "request_failed",
                    method=request.method,
                    path=request.url.path,
                    elapsed_ms=round(elapsed, 2),
                    error=str(exc),
                )
                raise

            elapsed = (time.perf_counter() - start) * 1000
            logger.info(
                "request_completed",
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                elapsed_ms=round(elapsed, 2),
            )
            response.headers["X-Request-ID"] = request_id
            return response
