"""Pipeline metrics using Prometheus client for production observability."""

import time
from contextlib import contextmanager
from typing import Generator, Optional

from prometheus_client import Counter, Gauge, Histogram, start_http_server

from src.utils.logger import get_logger

logger = get_logger(__name__)

# ── Prometheus metrics ─────────────────────────────────────────────────────────

DOCS_INGESTED = Counter(
    "pipeline_docs_ingested_total",
    "Total documents ingested",
    ["source_type"],
)
DOCS_PROCESSED = Counter(
    "pipeline_docs_processed_total",
    "Total documents processed successfully",
    ["stage"],
)
DOCS_FAILED = Counter(
    "pipeline_docs_failed_total",
    "Total documents that failed processing",
    ["stage"],
)
STAGE_DURATION = Histogram(
    "pipeline_stage_duration_seconds",
    "Processing duration per stage",
    ["stage"],
    buckets=[0.1, 0.5, 1, 5, 10, 30, 60, 120, 300],
)
CHUNKS_CREATED = Counter(
    "pipeline_chunks_created_total",
    "Total text chunks created",
)
EMBEDDINGS_GENERATED = Counter(
    "pipeline_embeddings_generated_total",
    "Total embeddings generated",
)
LLM_CALLS = Counter(
    "pipeline_llm_calls_total",
    "Total LLM API calls",
    ["call_type", "status"],
)
ACTIVE_DOCS = Gauge(
    "pipeline_active_documents",
    "Documents currently being processed",
)


class PipelineMetrics:
    """Convenience wrapper around Prometheus metrics with timing helpers."""

    def __init__(self, enable_server: bool = False, port: int = 8000) -> None:
        if enable_server:
            try:
                start_http_server(port)
                logger.info("metrics_server_started", port=port)
            except OSError:
                logger.warning("metrics_server_already_running", port=port)

    @contextmanager
    def time_stage(self, stage: str) -> Generator[None, None, None]:
        """Context manager that records stage duration and updates counters."""
        ACTIVE_DOCS.inc()
        start = time.perf_counter()
        try:
            yield
            DOCS_PROCESSED.labels(stage=stage).inc()
        except Exception:
            DOCS_FAILED.labels(stage=stage).inc()
            raise
        finally:
            elapsed = time.perf_counter() - start
            STAGE_DURATION.labels(stage=stage).observe(elapsed)
            ACTIVE_DOCS.dec()
            logger.debug("stage_completed", stage=stage, duration_s=round(elapsed, 3))

    @staticmethod
    def record_ingestion(source_type: str) -> None:
        DOCS_INGESTED.labels(source_type=source_type).inc()

    @staticmethod
    def record_chunks(count: int) -> None:
        CHUNKS_CREATED.inc(count)

    @staticmethod
    def record_embeddings(count: int) -> None:
        EMBEDDINGS_GENERATED.inc(count)

    @staticmethod
    def record_llm_call(call_type: str, success: bool) -> None:
        LLM_CALLS.labels(call_type=call_type, status="success" if success else "error").inc()
