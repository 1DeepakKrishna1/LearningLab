"""FastAPI gateway in front of the local SLLM.

Endpoints:
    GET  /health        -> liveness + readiness of the knowledge base
    POST /chat          -> grounded answer (non-streaming JSON)
    POST /stream        -> grounded answer streamed token-by-token (text/plain)

Run:
    uvicorn main:app --reload --port 8000
"""
import asyncio
import json

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from ollama import AsyncClient
from pydantic import BaseModel

import config
import rag

app = FastAPI(title="SLLM Gateway", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)

_aclient = AsyncClient(host=config.OLLAMA_HOST)


class Chat(BaseModel):
    message: str


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "chat_model": config.CHAT_MODEL,
        "embed_model": config.EMBED_MODEL,
        "knowledge_base_ready": rag.is_ready(),
    }


@app.post("/chat")
async def chat(req: Chat):
    """Non-streaming grounded answer."""
    messages, sources = rag.build_messages(req.message)
    resp = await _aclient.chat(
        model=config.CHAT_MODEL,
        messages=messages,
        options={"temperature": config.TEMPERATURE, "num_ctx": config.NUM_CTX},
    )
    return {"reply": resp["message"]["content"], "sources": sources}


@app.post("/stream")
async def stream(req: Chat):
    """Stream the answer token-by-token.

    The body is newline-delimited JSON events:
        {"type": "sources", "sources": [...]}      (sent first)
        {"type": "token", "content": "..."}        (many)
        {"type": "done"}                           (last)
    """
    messages, sources = rag.build_messages(req.message)

    async def gen():
        yield json.dumps({"type": "sources", "sources": sources}) + "\n"
        try:
            async for part in await _aclient.chat(
                model=config.CHAT_MODEL,
                messages=messages,
                stream=True,
                options={"temperature": config.TEMPERATURE, "num_ctx": config.NUM_CTX},
            ):
                token = part["message"]["content"]
                if token:
                    yield json.dumps({"type": "token", "content": token}) + "\n"
        except Exception as exc:  # noqa: BLE001
            yield json.dumps({"type": "error", "content": str(exc)}) + "\n"
        yield json.dumps({"type": "done"}) + "\n"

    return StreamingResponse(gen(), media_type="application/x-ndjson")
