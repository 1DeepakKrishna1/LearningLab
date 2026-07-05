"""In-memory observability: logs, traces, metrics, and frontend events.

Designed to mirror the project's existing pattern of bounded in-memory stores
served via FastAPI routes. Buckets are capped to avoid unbounded growth.
"""
from __future__ import annotations

import uuid
import time
import threading
from collections import deque
from datetime import datetime, timedelta
from typing import Any, Deque, Dict, List, Optional


# ── Tunables ───────────────────────────────────────────────────────
MAX_LOGS         = 5000
MAX_TRACES       = 1000
MAX_METRIC_POINTS = 2000   # per metric series
MAX_FRONT_EVENTS = 2000

LOG_LEVELS = ("debug", "info", "warn", "error", "critical")

_lock = threading.RLock()


# ── Stores ─────────────────────────────────────────────────────────
logs_buffer: Deque[Dict[str, Any]] = deque(maxlen=MAX_LOGS)
traces_db: Dict[str, Dict[str, Any]] = {}
_traces_order: Deque[str] = deque(maxlen=MAX_TRACES)
metrics_series: Dict[str, Deque[Dict[str, Any]]] = {}
frontend_events: Deque[Dict[str, Any]] = deque(maxlen=MAX_FRONT_EVENTS)

# Per-request counters used to derive rate/error/latency aggregates
_minute_buckets: Dict[str, Dict[str, Any]] = {}


def _now_iso() -> str:
    return datetime.utcnow().isoformat() + "Z"


def _minute_key(dt: Optional[datetime] = None) -> str:
    dt = dt or datetime.utcnow()
    return dt.strftime("%Y-%m-%dT%H:%M")


# ── Logging ────────────────────────────────────────────────────────
def log(
    level: str,
    message: str,
    *,
    source: str = "backend",
    logger: str = "app",
    trace_id: Optional[str] = None,
    span_id: Optional[str] = None,
    user_id: Optional[str] = None,
    workflow_id: Optional[str] = None,
    extra: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    lvl = (level or "info").lower()
    if lvl not in LOG_LEVELS:
        lvl = "info"
    entry = {
        "id": str(uuid.uuid4()),
        "ts": _now_iso(),
        "level": lvl,
        "source": source,
        "logger": logger,
        "message": message[:2000] if isinstance(message, str) else str(message)[:2000],
        "trace_id": trace_id,
        "span_id": span_id,
        "user_id": user_id,
        "workflow_id": workflow_id,
        "extra": extra or {},
    }
    with _lock:
        logs_buffer.append(entry)
    return entry


def query_logs(
    *,
    level: str = "",
    source: str = "",
    logger: str = "",
    workflow_id: str = "",
    search: str = "",
    since: Optional[str] = None,
    limit: int = 200,
) -> List[Dict[str, Any]]:
    with _lock:
        items = list(logs_buffer)
    items.reverse()
    out: List[Dict[str, Any]] = []
    sl = search.lower() if search else ""
    for it in items:
        if level and it["level"] != level:
            continue
        if source and it["source"] != source:
            continue
        if logger and it["logger"] != logger:
            continue
        if workflow_id and it["workflow_id"] != workflow_id:
            continue
        if since and it["ts"] <= since:
            continue
        if sl and sl not in it["message"].lower() and sl not in (it["logger"] or "").lower():
            continue
        out.append(it)
        if len(out) >= limit:
            break
    return out


# ── Tracing ────────────────────────────────────────────────────────
def start_trace(
    name: str,
    *,
    source: str = "backend",
    attributes: Optional[Dict[str, Any]] = None,
    user_id: Optional[str] = None,
) -> Dict[str, Any]:
    trace_id = uuid.uuid4().hex
    span_id = uuid.uuid4().hex[:16]
    started_at = datetime.utcnow()
    trace = {
        "trace_id": trace_id,
        "name": name,
        "source": source,
        "user_id": user_id,
        "status": "running",
        "started_at": started_at.isoformat() + "Z",
        "ended_at": None,
        "duration_ms": None,
        "attributes": attributes or {},
        "spans": [
            {
                "span_id": span_id,
                "parent_span_id": None,
                "name": name,
                "started_at": started_at.isoformat() + "Z",
                "ended_at": None,
                "duration_ms": None,
                "status": "running",
                "attributes": {},
                "events": [],
            }
        ],
    }
    with _lock:
        traces_db[trace_id] = trace
        _traces_order.append(trace_id)
        # Evict oldest if we exceeded cap
        if len(traces_db) > MAX_TRACES:
            evict = traces_db.keys() - set(_traces_order)
            for tid in evict:
                traces_db.pop(tid, None)
    return {"trace_id": trace_id, "root_span_id": span_id}


def add_span(
    trace_id: str,
    name: str,
    *,
    parent_span_id: Optional[str] = None,
    attributes: Optional[Dict[str, Any]] = None,
) -> Optional[str]:
    with _lock:
        trace = traces_db.get(trace_id)
        if not trace:
            return None
        span_id = uuid.uuid4().hex[:16]
        trace["spans"].append({
            "span_id": span_id,
            "parent_span_id": parent_span_id or trace["spans"][0]["span_id"],
            "name": name,
            "started_at": _now_iso(),
            "ended_at": None,
            "duration_ms": None,
            "status": "running",
            "attributes": attributes or {},
            "events": [],
        })
        return span_id


def end_span(
    trace_id: str,
    span_id: str,
    *,
    status: str = "ok",
    attributes: Optional[Dict[str, Any]] = None,
) -> None:
    with _lock:
        trace = traces_db.get(trace_id)
        if not trace:
            return
        for sp in trace["spans"]:
            if sp["span_id"] == span_id and sp["ended_at"] is None:
                end_dt = datetime.utcnow()
                start_dt = datetime.fromisoformat(sp["started_at"].rstrip("Z"))
                sp["ended_at"] = end_dt.isoformat() + "Z"
                sp["duration_ms"] = int((end_dt - start_dt).total_seconds() * 1000)
                sp["status"] = status
                if attributes:
                    sp["attributes"].update(attributes)
                break


def end_trace(trace_id: str, *, status: str = "ok") -> None:
    with _lock:
        trace = traces_db.get(trace_id)
        if not trace:
            return
        end_dt = datetime.utcnow()
        start_dt = datetime.fromisoformat(trace["started_at"].rstrip("Z"))
        trace["ended_at"] = end_dt.isoformat() + "Z"
        trace["duration_ms"] = int((end_dt - start_dt).total_seconds() * 1000)
        trace["status"] = status
        # Close root span if still open
        root = trace["spans"][0]
        if root["ended_at"] is None:
            root["ended_at"] = trace["ended_at"]
            root["duration_ms"] = trace["duration_ms"]
            root["status"] = status


def query_traces(
    *,
    source: str = "",
    status: str = "",
    name: str = "",
    only_active: bool = False,
    limit: int = 100,
) -> List[Dict[str, Any]]:
    with _lock:
        ids = list(_traces_order)
    ids.reverse()
    out: List[Dict[str, Any]] = []
    for tid in ids:
        t = traces_db.get(tid)
        if not t:
            continue
        if source and t["source"] != source:
            continue
        if status and t["status"] != status:
            continue
        if name and name.lower() not in t["name"].lower():
            continue
        if only_active and t["status"] != "running":
            continue
        out.append({
            "trace_id": t["trace_id"],
            "name": t["name"],
            "source": t["source"],
            "status": t["status"],
            "started_at": t["started_at"],
            "ended_at": t["ended_at"],
            "duration_ms": t["duration_ms"],
            "span_count": len(t["spans"]),
            "attributes": t["attributes"],
        })
        if len(out) >= limit:
            break
    return out


def get_trace(trace_id: str) -> Optional[Dict[str, Any]]:
    with _lock:
        t = traces_db.get(trace_id)
        return dict(t) if t else None


# ── Metrics ────────────────────────────────────────────────────────
def record_metric(
    name: str,
    value: float,
    *,
    labels: Optional[Dict[str, str]] = None,
) -> None:
    point = {
        "ts": _now_iso(),
        "value": float(value),
        "labels": labels or {},
    }
    with _lock:
        series = metrics_series.setdefault(name, deque(maxlen=MAX_METRIC_POINTS))
        series.append(point)


def record_request(
    *,
    method: str,
    path: str,
    status_code: int,
    duration_ms: float,
) -> None:
    """Bump per-minute aggregate counters for the dashboard."""
    is_error = status_code >= 500
    is_client = 400 <= status_code < 500
    record_metric("http.requests", 1, labels={"method": method, "status": str(status_code)})
    record_metric("http.duration_ms", duration_ms, labels={"path": path})
    if is_error:
        record_metric("http.errors", 1, labels={"path": path})

    with _lock:
        bucket = _minute_buckets.setdefault(
            _minute_key(),
            {"requests": 0, "errors": 0, "client_errors": 0, "duration_total": 0.0},
        )
        bucket["requests"] += 1
        bucket["duration_total"] += duration_ms
        if is_error:
            bucket["errors"] += 1
        if is_client:
            bucket["client_errors"] += 1

        # Keep last 60 minutes only
        cutoff = (datetime.utcnow() - timedelta(minutes=60)).strftime("%Y-%m-%dT%H:%M")
        stale = [k for k in _minute_buckets if k < cutoff]
        for k in stale:
            _minute_buckets.pop(k, None)


def metrics_snapshot(window_minutes: int = 60) -> Dict[str, Any]:
    """Return time-series suited to the dashboard charts."""
    now = datetime.utcnow().replace(second=0, microsecond=0)
    buckets: List[Dict[str, Any]] = []
    with _lock:
        snap = dict(_minute_buckets)
    for i in range(window_minutes - 1, -1, -1):
        t = now - timedelta(minutes=i)
        key = t.strftime("%Y-%m-%dT%H:%M")
        b = snap.get(key, {"requests": 0, "errors": 0, "client_errors": 0, "duration_total": 0.0})
        avg = (b["duration_total"] / b["requests"]) if b["requests"] else 0
        buckets.append({
            "minute": key,
            "requests": b["requests"],
            "errors": b["errors"],
            "client_errors": b["client_errors"],
            "avg_duration_ms": round(avg, 2),
        })

    totals = {
        "requests": sum(b["requests"] for b in buckets),
        "errors": sum(b["errors"] for b in buckets),
        "client_errors": sum(b["client_errors"] for b in buckets),
    }
    total_dur = sum((b["avg_duration_ms"] * b["requests"]) for b in buckets)
    totals["avg_duration_ms"] = round((total_dur / totals["requests"]) if totals["requests"] else 0, 2)
    totals["error_rate_pct"] = round((totals["errors"] / totals["requests"] * 100) if totals["requests"] else 0, 2)

    # Frontend event counts
    with _lock:
        fe_count = len(frontend_events)
        fe_recent = sum(1 for e in frontend_events if e.get("ts", "") >= (now - timedelta(minutes=5)).isoformat() + "Z")
        active_traces = sum(1 for t in traces_db.values() if t["status"] == "running")
        finished = [t for t in traces_db.values() if t["status"] != "running" and t.get("duration_ms")]
    durations = [t["duration_ms"] for t in finished]
    durations.sort()
    p95 = durations[int(len(durations) * 0.95) - 1] if durations else 0
    p50 = durations[int(len(durations) * 0.5) - 1] if durations else 0

    return {
        "window_minutes": window_minutes,
        "series": buckets,
        "totals": totals,
        "traces": {
            "active": active_traces,
            "finished": len(finished),
            "p50_ms": p50,
            "p95_ms": p95,
        },
        "frontend": {
            "events_total": fe_count,
            "events_5m": fe_recent,
        },
        "logs": {
            "total": len(logs_buffer),
            "by_level": _log_level_breakdown(),
        },
    }


def _log_level_breakdown() -> Dict[str, int]:
    out = {lvl: 0 for lvl in LOG_LEVELS}
    with _lock:
        for entry in logs_buffer:
            lvl = entry.get("level", "info")
            if lvl in out:
                out[lvl] += 1
    return out


# ── Frontend events ────────────────────────────────────────────────
def record_frontend_event(event: Dict[str, Any]) -> Dict[str, Any]:
    entry = {
        "id": str(uuid.uuid4()),
        "ts": event.get("ts") or _now_iso(),
        "kind": event.get("kind", "event"),
        "name": event.get("name", "unknown"),
        "url": event.get("url"),
        "user_id": event.get("user_id"),
        "session_id": event.get("session_id"),
        "duration_ms": event.get("duration_ms"),
        "status": event.get("status"),
        "attributes": event.get("attributes") or {},
    }
    with _lock:
        frontend_events.append(entry)
    # Also surface as metric points for the dashboard
    record_metric(f"frontend.{entry['kind']}", 1, labels={"name": entry["name"]})
    return entry


def query_frontend_events(
    *,
    kind: str = "",
    search: str = "",
    limit: int = 200,
) -> List[Dict[str, Any]]:
    with _lock:
        items = list(frontend_events)
    items.reverse()
    sl = search.lower() if search else ""
    out: List[Dict[str, Any]] = []
    for it in items:
        if kind and it["kind"] != kind:
            continue
        if sl and sl not in (it.get("name") or "").lower() and sl not in (it.get("url") or "").lower():
            continue
        out.append(it)
        if len(out) >= limit:
            break
    return out


# ── Snapshot for stream endpoint ───────────────────────────────────
def snapshot_since(
    *,
    log_since: Optional[str] = None,
    trace_since: Optional[str] = None,
    event_since: Optional[str] = None,
    limit: int = 100,
) -> Dict[str, Any]:
    with _lock:
        recent_logs = [l for l in logs_buffer if (not log_since or l["ts"] > log_since)]
        recent_logs = recent_logs[-limit:]
        all_traces = []
        for tid in list(_traces_order)[-limit:]:
            t = traces_db.get(tid)
            if not t:
                continue
            if trace_since and (t.get("ended_at") or t["started_at"]) <= trace_since:
                continue
            all_traces.append({
                "trace_id": t["trace_id"],
                "name": t["name"],
                "source": t["source"],
                "status": t["status"],
                "started_at": t["started_at"],
                "ended_at": t["ended_at"],
                "duration_ms": t["duration_ms"],
                "span_count": len(t["spans"]),
            })
        recent_events = [e for e in frontend_events if (not event_since or e["ts"] > event_since)]
        recent_events = recent_events[-limit:]
    return {
        "logs": recent_logs,
        "traces": all_traces,
        "frontend_events": recent_events,
        "metrics": metrics_snapshot(window_minutes=15),
        "server_time": _now_iso(),
    }
