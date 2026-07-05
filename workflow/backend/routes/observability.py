"""Observability API: logs, traces, metrics, frontend events, live stream."""
from fastapi import APIRouter, Query, Body
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

import observability as obs


router = APIRouter()


# ── Logs ───────────────────────────────────────────────────────────
class LogIn(BaseModel):
    level: str = "info"
    message: str
    source: str = "frontend"
    logger: str = "app"
    trace_id: Optional[str] = None
    span_id: Optional[str] = None
    user_id: Optional[str] = None
    workflow_id: Optional[str] = None
    extra: Dict[str, Any] = Field(default_factory=dict)


class LogBatch(BaseModel):
    entries: List[LogIn]


@router.post("/logs")
def ingest_log(body: LogIn):
    return obs.log(
        body.level, body.message,
        source=body.source, logger=body.logger,
        trace_id=body.trace_id, span_id=body.span_id,
        user_id=body.user_id, workflow_id=body.workflow_id,
        extra=body.extra,
    )


@router.post("/logs/batch")
def ingest_log_batch(body: LogBatch):
    return {"ingested": [obs.log(
        e.level, e.message,
        source=e.source, logger=e.logger,
        trace_id=e.trace_id, span_id=e.span_id,
        user_id=e.user_id, workflow_id=e.workflow_id,
        extra=e.extra,
    ) for e in body.entries]}


@router.get("/logs")
def list_logs(
    level: str = Query(""),
    source: str = Query(""),
    logger: str = Query(""),
    workflow_id: str = Query(""),
    search: str = Query(""),
    since: str = Query(""),
    limit: int = Query(200, ge=1, le=2000),
):
    rows = obs.query_logs(
        level=level, source=source, logger=logger,
        workflow_id=workflow_id, search=search,
        since=since or None, limit=limit,
    )
    return {"rows": rows, "count": len(rows)}


# ── Traces ─────────────────────────────────────────────────────────
class TraceStart(BaseModel):
    name: str
    source: str = "frontend"
    attributes: Dict[str, Any] = Field(default_factory=dict)
    user_id: Optional[str] = None


class TraceEnd(BaseModel):
    trace_id: str
    status: str = "ok"


class SpanIn(BaseModel):
    trace_id: str
    name: str
    parent_span_id: Optional[str] = None
    attributes: Dict[str, Any] = Field(default_factory=dict)


class SpanEnd(BaseModel):
    trace_id: str
    span_id: str
    status: str = "ok"
    attributes: Dict[str, Any] = Field(default_factory=dict)


@router.post("/traces/start")
def start_trace(body: TraceStart):
    return obs.start_trace(body.name, source=body.source, attributes=body.attributes, user_id=body.user_id)


@router.post("/traces/end")
def end_trace(body: TraceEnd):
    obs.end_trace(body.trace_id, status=body.status)
    return {"ok": True}


@router.post("/traces/span")
def start_span(body: SpanIn):
    span_id = obs.add_span(body.trace_id, body.name, parent_span_id=body.parent_span_id, attributes=body.attributes)
    return {"span_id": span_id}


@router.post("/traces/span/end")
def end_span(body: SpanEnd):
    obs.end_span(body.trace_id, body.span_id, status=body.status, attributes=body.attributes)
    return {"ok": True}


@router.get("/traces")
def list_traces(
    source: str = Query(""),
    status: str = Query(""),
    name: str = Query(""),
    only_active: bool = Query(False),
    limit: int = Query(100, ge=1, le=500),
):
    rows = obs.query_traces(source=source, status=status, name=name, only_active=only_active, limit=limit)
    return {"rows": rows, "count": len(rows)}


@router.get("/traces/{trace_id}")
def get_trace(trace_id: str):
    t = obs.get_trace(trace_id)
    if not t:
        return {"error": "not_found"}
    return t


# ── Metrics ────────────────────────────────────────────────────────
class MetricIn(BaseModel):
    name: str
    value: float
    labels: Dict[str, str] = Field(default_factory=dict)


@router.post("/metrics")
def record_metric(body: MetricIn):
    obs.record_metric(body.name, body.value, labels=body.labels)
    return {"ok": True}


@router.get("/metrics/snapshot")
def metrics_snapshot(window_minutes: int = Query(60, ge=5, le=240)):
    return obs.metrics_snapshot(window_minutes=window_minutes)


# ── Frontend events ────────────────────────────────────────────────
class FrontendEventIn(BaseModel):
    kind: str = "event"          # event | nav | click | api | error
    name: str
    url: Optional[str] = None
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    duration_ms: Optional[float] = None
    status: Optional[str] = None
    attributes: Dict[str, Any] = Field(default_factory=dict)
    ts: Optional[str] = None


class FrontendEventBatch(BaseModel):
    entries: List[FrontendEventIn]


@router.post("/events")
def record_event(body: FrontendEventIn):
    return obs.record_frontend_event(body.model_dump())


@router.post("/events/batch")
def record_event_batch(body: FrontendEventBatch):
    return {"ingested": [obs.record_frontend_event(e.model_dump()) for e in body.entries]}


@router.get("/events")
def list_events(
    kind: str = Query(""),
    search: str = Query(""),
    limit: int = Query(200, ge=1, le=2000),
):
    rows = obs.query_frontend_events(kind=kind, search=search, limit=limit)
    return {"rows": rows, "count": len(rows)}


# ── Live stream snapshot (polled by Live Monitor) ──────────────────
@router.get("/stream")
def stream_snapshot(
    log_since: str = Query(""),
    trace_since: str = Query(""),
    event_since: str = Query(""),
    limit: int = Query(100, ge=1, le=500),
):
    return obs.snapshot_since(
        log_since=log_since or None,
        trace_since=trace_since or None,
        event_since=event_since or None,
        limit=limit,
    )


@router.get("/summary")
def summary():
    return obs.metrics_snapshot(window_minutes=60)
