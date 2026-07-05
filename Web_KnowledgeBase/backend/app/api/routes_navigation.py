"""Knowledge navigation: N-level tree, breadcrumbs, page content, related content."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ..models import Breadcrumb, NavNode, PageContent, RelatedPage
from ..rag.knowledge_base import get_kb

router = APIRouter(tags=["navigation"])


@router.get("/navigation", response_model=list[NavNode])
def navigation() -> list[NavNode]:
    kb = get_kb()
    if not kb.ready:
        raise HTTPException(status_code=409, detail="No knowledge base loaded.")
    return [NavNode(**node) for node in kb.nav_tree()]


@router.get("/content/{page_id}", response_model=PageContent)
def page_content(page_id: str) -> PageContent:
    kb = get_kb()
    page = kb.pages.get(page_id)
    if not page:
        raise HTTPException(status_code=404, detail="Page not found")
    related = [
        RelatedPage(page_id=p.page_id, title=p.title, url=p.url, score=round(score, 4))
        for score, p in kb.related(page_id, top_k=5)
    ]
    return PageContent(
        page_id=page.page_id,
        url=page.url,
        title=page.title,
        depth=page.depth,
        text=page.text,
        breadcrumbs=[Breadcrumb(**b) for b in kb.breadcrumbs(page_id)],
        related=related,
    )
