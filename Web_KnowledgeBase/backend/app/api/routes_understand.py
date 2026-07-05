"""Content understanding: summarization, topic extraction, insights, classification."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ..llm import agent
from ..models import UnderstandRequest, UnderstandResponse
from ..rag.knowledge_base import get_kb

router = APIRouter(tags=["understanding"])


@router.post("/understand", response_model=UnderstandResponse)
def understand(req: UnderstandRequest) -> UnderstandResponse:
    title = ""
    url = ""
    text = req.text or ""

    if req.page_id:
        kb = get_kb()
        page = kb.pages.get(req.page_id)
        if not page:
            raise HTTPException(status_code=404, detail="Page not found")
        text, title, url = page.text, page.title, page.url

    if not text.strip():
        raise HTTPException(status_code=400, detail="Provide either a page_id or non-empty text.")

    result = agent.understand(req.mode, text, title)
    return UnderstandResponse(mode=req.mode, result=result, source_title=title, source_url=url)
