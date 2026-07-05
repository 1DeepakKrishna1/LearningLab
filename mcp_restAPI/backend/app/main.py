"""FastAPI application entrypoint."""
from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .routers import chat, health, specs

logging.basicConfig(level=logging.INFO)

settings = get_settings()

app = FastAPI(
    title="RESTAPI AI Agent",
    description="LLM-powered agent that consumes OpenAPI specs and invokes REST APIs.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(specs.router)
app.include_router(chat.router)


@app.get("/")
async def root() -> dict:
    return {"name": "RESTAPI AI Agent", "docs": "/docs", "health": "/api/health"}
