"""Ingestion + knowledge-base status endpoints."""
from __future__ import annotations

import os

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from ..config import get_settings
from ..extractors import supported_extensions
from ..models import (
    DeleteRequest,
    DeleteResult,
    IngestRequest,
    JobStatus,
    KBStatus,
    SourceItem,
    SourcesResponse,
)
from ..rag.knowledge_base import get_kb
from ..services import ingest

router = APIRouter(tags=["ingest"])


@router.post("/ingest", response_model=JobStatus)
def create_ingest(req: IngestRequest) -> JobStatus:
    if not req.url.startswith(("http://", "https://")):
        raise HTTPException(status_code=400, detail="URL must start with http:// or https://")
    job_id = ingest.start_ingest(req.url, req.max_depth, req.max_pages, req.same_domain_only)
    return ingest.get_job(job_id)  # type: ignore[return-value]


@router.get("/ingest/formats")
def ingest_formats() -> dict:
    settings = get_settings()
    return {
        "extensions": supported_extensions(),
        "max_files": settings.max_upload_files,
        "max_file_mb": settings.max_upload_mb,
    }


@router.post("/ingest/files", response_model=JobStatus)
async def create_file_ingest(
    files: list[UploadFile] = File(...),
    append: bool = Form(True),
    start_page: int | None = Form(None),
    end_page: int | None = Form(None),
) -> JobStatus:
    settings = get_settings()
    max_bytes = settings.max_upload_mb * 1024 * 1024
    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded.")
    if len(files) > settings.max_upload_files:
        raise HTTPException(status_code=400, detail=f"Too many files (max {settings.max_upload_files}).")
    if start_page is not None and start_page < 1:
        raise HTTPException(status_code=400, detail="start_page must be >= 1.")
    if end_page is not None and start_page is not None and end_page < start_page:
        raise HTTPException(status_code=400, detail="end_page must be >= start_page.")

    items: list[tuple[str, str | None, bytes]] = []
    for f in files:
        data = await f.read()
        if len(data) > max_bytes:
            raise HTTPException(
                status_code=400,
                detail=f"{f.filename} is {len(data) // (1024 * 1024)} MB, over the {settings.max_upload_mb} MB limit. "
                f"Raise MAX_UPLOAD_MB in the backend .env to allow larger files.",
            )
        items.append((f.filename or "document", f.content_type, data))

    job_id = ingest.start_file_ingest(items, append, start_page, end_page)
    return ingest.get_job(job_id)  # type: ignore[return-value]


@router.get("/ingest/{job_id}", response_model=JobStatus)
def ingest_status(job_id: str) -> JobStatus:
    job = ingest.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


def _kb_dir() -> str:
    return os.path.join(get_settings().data_dir, "kb")


def _delete_result(kb, removed_pages: int, removed_chunks: int) -> DeleteResult:
    # Persist the new state: save if anything remains, otherwise wipe the dir.
    if kb.pages:
        kb.save(_kb_dir())
    else:
        kb.clear(_kb_dir())
    return DeleteResult(
        removed_pages=removed_pages,
        removed_chunks=removed_chunks,
        page_count=len(kb.pages),
        chunk_count=kb.store.size if kb.store else 0,
        ready=kb.ready,
    )


@router.get("/sources", response_model=SourcesResponse)
def list_sources() -> SourcesResponse:
    kb = get_kb()
    items = [
        SourceItem(page_id=p.page_id, title=p.title, url=p.url, source=p.source, depth=p.depth)
        for p in kb.sources_list()
    ]
    return SourcesResponse(
        domain=kb.meta.domain,
        web_pages=sum(1 for p in kb.pages.values() if p.source == "web"),
        file_pages=sum(1 for p in kb.pages.values() if p.source == "file"),
        items=items,
    )


@router.delete("/kb", response_model=DeleteResult)
def clear_kb() -> DeleteResult:
    kb = get_kb()
    pages = len(kb.pages)
    chunks = kb.store.size if kb.store else 0
    kb.clear(_kb_dir())
    return DeleteResult(removed_pages=pages, removed_chunks=chunks, page_count=0, chunk_count=0, ready=False)


@router.post("/kb/delete", response_model=DeleteResult)
def delete_from_kb(req: DeleteRequest) -> DeleteResult:
    kb = get_kb()
    if not req.source and not req.page_ids:
        raise HTTPException(status_code=400, detail="Provide page_ids or a source to delete.")
    if req.source:
        removed_pages, removed_chunks = kb.delete_by_source(req.source)
    else:
        removed_pages, removed_chunks = kb.delete_pages(set(req.page_ids))
    return _delete_result(kb, removed_pages, removed_chunks)


@router.get("/status", response_model=KBStatus)
def kb_status() -> KBStatus:
    kb = get_kb()
    settings = get_settings()
    return KBStatus(
        ready=kb.ready,
        seed_url=kb.meta.seed_url,
        domain=kb.meta.domain,
        page_count=len(kb.pages),
        chunk_count=kb.store.size if kb.store else 0,
        max_depth=kb.meta.max_depth,
        embedding_model=kb.meta.embedding_model or settings.embedding_model,
        llm_model=settings.llm_model,
    )
