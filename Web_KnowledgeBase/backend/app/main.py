"""FastAPI application entrypoint for the LLM Knowledge Portal Agent."""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api import (
    routes_chat,
    routes_ingest,
    routes_navigation,
    routes_search,
    routes_understand,
)
from .config import get_settings

settings = get_settings()

app = FastAPI(
    title="LLM Knowledge Portal AI Agent",
    version="1.0.0",
    description="Build an AI knowledge agent from any web portal: crawl, embed (FAISS), "
    "search, chat, navigate, and reason over the content.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

API = "/api"
app.include_router(routes_ingest.router, prefix=API)
app.include_router(routes_search.router, prefix=API)
app.include_router(routes_chat.router, prefix=API)
app.include_router(routes_navigation.router, prefix=API)
app.include_router(routes_understand.router, prefix=API)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
