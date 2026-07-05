"""Conversational assistance: agentic Q&A (JSON) and fast streaming RAG (SSE)."""
from __future__ import annotations

import json

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from ..config import get_settings
from ..llm import agent
from ..models import ChatRequest, ChatResponse
from ..rag.knowledge_base import get_kb

router = APIRouter(tags=["chat"])


@router.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest) -> ChatResponse:
    """Agentic, multi-step answer with cross-document retrieval (non-streaming)."""
    kb = get_kb()
    if not kb.ready:
        raise HTTPException(status_code=409, detail="No knowledge base loaded. Ingest a portal first.")
    top_k = req.top_k or get_settings().top_k
    answer, sources, steps = agent.agentic_answer(kb, req.message, req.history, top_k)
    return ChatResponse(answer=answer, sources=sources, steps=steps)


@router.post("/chat/stream")
def chat_stream(req: ChatRequest):
    """Fast single-pass RAG with token streaming over Server-Sent Events."""
    kb = get_kb()
    if not kb.ready:
        raise HTTPException(status_code=409, detail="No knowledge base loaded. Ingest a portal first.")
    top_k = req.top_k or get_settings().top_k
    messages, sources = agent.prepare_single_pass(kb, req.message, req.history, top_k)

    def event_stream():
        try:
            for token in agent.stream_answer(messages):
                yield f"data: {json.dumps({'type': 'token', 'text': token})}\n\n"
            payload = {"type": "sources", "sources": [s.model_dump() for s in sources]}
            yield f"data: {json.dumps(payload)}\n\n"
            yield f"data: {json.dumps({'type': 'done'})}\n\n"
        except Exception as exc:  # noqa: BLE001
            yield f"data: {json.dumps({'type': 'error', 'error': str(exc)})}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
