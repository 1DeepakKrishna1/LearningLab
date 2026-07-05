"""Semantic search / knowledge discovery."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ..config import get_settings
from ..llm.agent import _snippet
from ..models import SearchHit, SearchRequest, SearchResponse
from ..rag.knowledge_base import get_kb

router = APIRouter(tags=["search"])


@router.post("/search", response_model=SearchResponse)
def search(req: SearchRequest) -> SearchResponse:
    kb = get_kb()
    if not kb.ready:
        raise HTTPException(status_code=409, detail="No knowledge base loaded. Ingest a portal first.")
    top_k = req.top_k or get_settings().top_k
    hits = kb.search(req.query, top_k)
    return SearchResponse(
        query=req.query,
        hits=[
            SearchHit(
                score=round(score, 4),
                text=_snippet(rec.text, 500),
                url=rec.url,
                title=rec.title,
                page_id=rec.page_id,
                chunk_id=rec.chunk_id,
            )
            for score, rec in hits
        ],
    )
