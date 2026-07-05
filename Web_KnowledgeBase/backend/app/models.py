"""Pydantic request/response schemas shared across the API."""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field


# ---------- Ingestion ----------
class IngestRequest(BaseModel):
    url: str = Field(..., description="Seed web portal URL to crawl.")
    max_depth: Optional[int] = Field(None, ge=0, le=6)
    max_pages: Optional[int] = Field(None, ge=1, le=2000)
    same_domain_only: Optional[bool] = None


class JobStatus(BaseModel):
    job_id: str
    state: Literal["queued", "crawling", "indexing", "done", "error"]
    message: str = ""
    pages_crawled: int = 0
    pages_indexed: int = 0
    chunks_indexed: int = 0
    seed_url: str = ""
    domain: str = ""
    error: Optional[str] = None


# ---------- Knowledge base status ----------
class KBStatus(BaseModel):
    ready: bool
    seed_url: str = ""
    domain: str = ""
    page_count: int = 0
    chunk_count: int = 0
    max_depth: int = 0
    embedding_model: str = ""
    llm_model: str = ""


# ---------- Search ----------
class SearchRequest(BaseModel):
    query: str
    top_k: Optional[int] = Field(None, ge=1, le=50)


class SearchHit(BaseModel):
    score: float
    text: str
    url: str
    title: str
    page_id: str
    chunk_id: str


class SearchResponse(BaseModel):
    query: str
    hits: list[SearchHit]


# ---------- Chat ----------
class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    message: str
    history: list[ChatMessage] = Field(default_factory=list)
    top_k: Optional[int] = Field(None, ge=1, le=50)


class Source(BaseModel):
    n: int
    url: str
    title: str
    snippet: str
    page_id: str
    score: float


class ReasoningStep(BaseModel):
    type: Literal["thinking", "search", "answer"]
    detail: str


class ChatResponse(BaseModel):
    answer: str
    sources: list[Source]
    steps: list[ReasoningStep] = Field(default_factory=list)


# ---------- Navigation ----------
class NavNode(BaseModel):
    page_id: str
    title: str
    url: str
    depth: int
    children: list["NavNode"] = Field(default_factory=list)


class Breadcrumb(BaseModel):
    title: str
    url: str
    page_id: str


class PageContent(BaseModel):
    page_id: str
    url: str
    title: str
    depth: int
    text: str
    breadcrumbs: list[Breadcrumb]
    related: list["RelatedPage"] = Field(default_factory=list)


class RelatedPage(BaseModel):
    page_id: str
    title: str
    url: str
    score: float


# ---------- Sources / deletion ----------
class SourceItem(BaseModel):
    page_id: str
    title: str
    url: str
    source: str  # "web" | "file"
    depth: int


class SourcesResponse(BaseModel):
    domain: str = ""
    web_pages: int = 0
    file_pages: int = 0
    items: list[SourceItem] = Field(default_factory=list)


class DeleteRequest(BaseModel):
    page_ids: list[str] = Field(default_factory=list)
    source: Optional[Literal["web", "file"]] = None


class DeleteResult(BaseModel):
    removed_pages: int
    removed_chunks: int
    page_count: int
    chunk_count: int
    ready: bool


# ---------- Content understanding ----------
class UnderstandRequest(BaseModel):
    page_id: Optional[str] = None
    text: Optional[str] = None
    mode: Literal["summary", "topics", "insights", "classify"] = "summary"


class UnderstandResponse(BaseModel):
    mode: str
    result: str
    source_title: str = ""
    source_url: str = ""


NavNode.model_rebuild()
PageContent.model_rebuild()
