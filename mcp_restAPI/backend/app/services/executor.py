"""Dynamically build and execute REST requests against a target API."""
from __future__ import annotations

import json
import time
from typing import Any
from urllib.parse import quote

import httpx

from ..config import get_settings
from ..schemas import ApiCallRecord, AuthConfig, Operation
from .auth import apply_auth

_MAX_PREVIEW_CHARS = 4000


class MissingPathParameter(Exception):
    """Raised when a required path parameter was not supplied."""


def build_url(base_url: str, op: Operation, path_params: dict[str, Any]) -> str:
    """Substitute path parameters into the operation template."""
    path = op.path
    for param in op.parameters:
        if param.location != "path":
            continue
        token = "{" + param.name + "}"
        if token not in path:
            continue
        if param.name not in path_params or path_params[param.name] in (None, ""):
            raise MissingPathParameter(param.name)
        path = path.replace(token, quote(str(path_params[param.name]), safe=""))
    base = base_url.rstrip("/")
    return f"{base}/{path.lstrip('/')}"


def _parse_response_body(resp: httpx.Response) -> Any:
    """Parse JSON / XML / CSV / text responses into a preview-friendly value."""
    ctype = resp.headers.get("content-type", "").lower()
    text = resp.text or ""
    if "json" in ctype:
        try:
            return resp.json()
        except (json.JSONDecodeError, ValueError):
            pass
    # XML / CSV / plain text are returned as (possibly truncated) text; the LLM
    # can interpret them. Structured XML/CSV parsing can be layered on later.
    if len(text) > _MAX_PREVIEW_CHARS:
        return text[:_MAX_PREVIEW_CHARS] + f"\n...[truncated {len(text)} chars]"
    return text


def _truncate(value: Any) -> Any:
    """Bound the size of a value before it is sent back to the LLM/UI."""
    if isinstance(value, str):
        return value if len(value) <= _MAX_PREVIEW_CHARS else value[:_MAX_PREVIEW_CHARS] + "...[truncated]"
    try:
        encoded = json.dumps(value)
    except (TypeError, ValueError):
        return str(value)[:_MAX_PREVIEW_CHARS]
    if len(encoded) <= _MAX_PREVIEW_CHARS:
        return value
    # Too large to send verbatim: return a truncated string form.
    return encoded[:_MAX_PREVIEW_CHARS] + "...[truncated]"


async def execute_operation(
    *,
    base_url: str,
    op: Operation,
    auth: AuthConfig | None,
    path_params: dict[str, Any] | None = None,
    query: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    body: Any | None = None,
) -> ApiCallRecord:
    """Execute one REST call and return a structured record.

    Network/HTTP errors are captured in the record rather than raised, so the
    agent can reason about failures and retry.
    """
    settings = get_settings()
    path_params = path_params or {}
    query = {k: v for k, v in (query or {}).items() if v is not None}
    headers = dict(headers or {})

    record = ApiCallRecord(operation_id=op.operation_id, method=op.method, url="")

    try:
        url = build_url(base_url, op, path_params)
    except MissingPathParameter as exc:
        record.error = f"Missing required path parameter: {exc}"
        return record

    record.url = url
    headers, query = apply_auth(auth, headers, query)

    send_json = None
    send_content = None
    if body is not None and op.method in ("POST", "PUT", "PATCH", "DELETE"):
        ctype = op.request_content_type or "application/json"
        if "json" in ctype:
            send_json = body
            record.request_body = _truncate(body)
        else:
            send_content = body if isinstance(body, (str, bytes)) else json.dumps(body)
            headers.setdefault("Content-Type", ctype)
            record.request_body = _truncate(body)

    start = time.perf_counter()
    try:
        async with httpx.AsyncClient(timeout=settings.http_timeout, follow_redirects=True) as client:
            resp = await client.request(
                op.method,
                url,
                params=query or None,
                headers=headers or None,
                json=send_json,
                content=send_content,
            )
        record.duration_ms = round((time.perf_counter() - start) * 1000, 1)
        record.status_code = resp.status_code
        record.ok = resp.is_success
        record.response_preview = _truncate(_parse_response_body(resp))
        if not resp.is_success:
            record.error = f"HTTP {resp.status_code}"
    except httpx.HTTPError as exc:
        record.duration_ms = round((time.perf_counter() - start) * 1000, 1)
        record.error = f"Request failed: {exc}"

    return record
