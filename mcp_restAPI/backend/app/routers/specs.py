"""Endpoints for ingesting and managing OpenAPI/Swagger specs."""
from __future__ import annotations

from fastapi import APIRouter, File, HTTPException, Response, UploadFile

from ..config import get_settings
from ..openapi.loader import SpecLoadError, fetch_spec_from_url, parse_spec_text
from ..openapi.parser import parse_spec
from ..schemas import (
    IngestTextRequest,
    IngestUrlRequest,
    Operation,
    SpecSummary,
)
from ..services.search import search_operations
from ..storage import spec_store

router = APIRouter(prefix="/api/specs", tags=["specs"])


def _finalize(parsed, base_url_override: str | None):
    if base_url_override:
        parsed.base_url = base_url_override.rstrip("/")
    return parsed


@router.post("", response_model=SpecSummary, status_code=201)
async def ingest_from_url(req: IngestUrlRequest) -> SpecSummary:
    """Import a spec from a Swagger/OpenAPI URL."""
    settings = get_settings()
    try:
        raw = await fetch_spec_from_url(req.url, timeout=settings.http_timeout)
        parsed = _finalize(parse_spec(raw, source_url=req.url), req.base_url_override)
    except SpecLoadError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not parsed.operations:
        raise HTTPException(status_code=422, detail="No operations found in spec.")
    spec_id = spec_store.add(parsed, source=req.url)
    return spec_store.summary(spec_id)  # type: ignore[return-value]


@router.post("/upload", response_model=SpecSummary, status_code=201)
async def ingest_from_text(req: IngestTextRequest) -> SpecSummary:
    """Import a spec from pasted/uploaded JSON or YAML text."""
    try:
        raw = parse_spec_text(req.content)
        parsed = _finalize(parse_spec(raw), req.base_url_override)
    except SpecLoadError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not parsed.operations:
        raise HTTPException(status_code=422, detail="No operations found in spec.")
    source = req.filename or "uploaded"
    spec_id = spec_store.add(parsed, source=source)
    return spec_store.summary(spec_id)  # type: ignore[return-value]


@router.post("/upload-file", response_model=SpecSummary, status_code=201)
async def ingest_file(file: UploadFile = File(...)) -> SpecSummary:
    """Import a spec from a multipart file upload."""
    content = (await file.read()).decode("utf-8", errors="replace")
    try:
        raw = parse_spec_text(content)
        parsed = parse_spec(raw)
    except SpecLoadError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not parsed.operations:
        raise HTTPException(status_code=422, detail="No operations found in spec.")
    spec_id = spec_store.add(parsed, source=file.filename or "uploaded-file")
    return spec_store.summary(spec_id)  # type: ignore[return-value]


@router.get("", response_model=list[SpecSummary])
async def list_specs() -> list[SpecSummary]:
    return spec_store.list_summaries()


@router.get("/{spec_id}", response_model=SpecSummary)
async def get_spec(spec_id: str) -> SpecSummary:
    summary = spec_store.summary(spec_id)
    if summary is None:
        raise HTTPException(status_code=404, detail="Spec not found.")
    return summary


@router.get("/{spec_id}/operations", response_model=list[Operation])
async def list_operations(spec_id: str, q: str | None = None) -> list[Operation]:
    """List operations in a spec, optionally filtered by a NL search query."""
    parsed = spec_store.get(spec_id)
    if parsed is None:
        raise HTTPException(status_code=404, detail="Spec not found.")
    if q:
        return [op for op, _ in search_operations(parsed, q, limit=50)]
    return parsed.operations


@router.post("/{spec_id}/refresh", response_model=SpecSummary)
async def refresh_spec(spec_id: str) -> SpecSummary:
    """Re-fetch a URL-sourced spec to pick up definition changes."""
    parsed = spec_store.get(spec_id)
    if parsed is None:
        raise HTTPException(status_code=404, detail="Spec not found.")
    source = spec_store.source(spec_id)
    if not source.startswith(("http://", "https://")):
        raise HTTPException(status_code=400, detail="Spec was not imported from a URL; cannot refresh.")
    settings = get_settings()
    try:
        raw = await fetch_spec_from_url(source, timeout=settings.http_timeout)
        new_parsed = parse_spec(raw, source_url=source)
    except SpecLoadError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    spec_store.replace(spec_id, new_parsed, source)
    return spec_store.summary(spec_id)  # type: ignore[return-value]


@router.delete("/{spec_id}", status_code=204, response_class=Response)
async def delete_spec(spec_id: str) -> Response:
    if not spec_store.delete(spec_id):
        raise HTTPException(status_code=404, detail="Spec not found.")
    return Response(status_code=204)
