"""HTTP middleware that auto-creates a trace + log + metric per request."""
import time
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

import observability as obs


# Paths that should NOT be auto-traced (avoid feedback loops & polling noise)
_SKIP_PREFIXES = (
    "/observability/stream",
    "/observability/logs",
    "/observability/traces",
    "/observability/metrics",
    "/observability/events",
    "/health",
    "/docs",
    "/openapi.json",
    "/favicon",
)


class ObservabilityMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        skip = any(path.startswith(p) for p in _SKIP_PREFIXES)

        trace_id = None
        if not skip:
            t = obs.start_trace(
                f"{request.method} {path}",
                source="backend",
                attributes={
                    "http.method": request.method,
                    "http.path": path,
                    "http.query": str(request.url.query),
                },
            )
            trace_id = t["trace_id"]

        start = time.perf_counter()
        status_code = 500
        try:
            response = await call_next(request)
            status_code = response.status_code
        except Exception as exc:
            duration_ms = (time.perf_counter() - start) * 1000
            if trace_id:
                obs.end_trace(trace_id, status="error")
            obs.log(
                "error",
                f"Unhandled exception on {request.method} {path}: {exc}",
                source="backend",
                logger="http",
                trace_id=trace_id,
                extra={"exception": str(exc)},
            )
            obs.record_request(
                method=request.method, path=path, status_code=500, duration_ms=duration_ms
            )
            raise

        duration_ms = (time.perf_counter() - start) * 1000

        if not skip:
            level = "info"
            status = "ok"
            if status_code >= 500:
                level, status = "error", "error"
            elif status_code >= 400:
                level, status = "warn", "client_error"

            obs.log(
                level,
                f"{request.method} {path} -> {status_code} ({duration_ms:.1f}ms)",
                source="backend",
                logger="http",
                trace_id=trace_id,
                extra={
                    "method": request.method,
                    "path": path,
                    "status_code": status_code,
                    "duration_ms": round(duration_ms, 2),
                },
            )
            if trace_id:
                obs.end_trace(trace_id, status=status)

            obs.record_request(
                method=request.method, path=path, status_code=status_code, duration_ms=duration_ms
            )
            response.headers["X-Trace-Id"] = trace_id or ""
        return response
