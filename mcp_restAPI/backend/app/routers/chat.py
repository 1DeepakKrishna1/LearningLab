"""Chat + approval endpoints that drive the agent."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ..schemas import ApprovalDecisionRequest, ChatRequest, ChatResponse
from ..services.agent import Agent
from ..services.llm import LLMNotConfigured
from ..storage import session_store, spec_store

router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
async def chat(req: ChatRequest) -> ChatResponse:
    """Send a user message to the agent for a given spec/session."""
    parsed = spec_store.get(req.spec_id)
    if parsed is None:
        raise HTTPException(status_code=404, detail="Spec not found. Import a spec first.")

    session = session_store.get_or_create(req.session_id, req.spec_id)
    if req.auth is not None:
        session.auth = req.auth  # latest credentials win

    agent = Agent(session, parsed, session.auth)
    try:
        return await agent.handle_message(req.message)
    except LLMNotConfigured as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post("/approve", response_model=ChatResponse)
async def approve(req: ApprovalDecisionRequest) -> ChatResponse:
    """Approve or reject a pending mutating call and resume the agent."""
    session = session_store.get(req.session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found.")
    parsed = spec_store.get(session.spec_id)
    if parsed is None:
        raise HTTPException(status_code=404, detail="Spec for this session no longer exists.")

    agent = Agent(session, parsed, session.auth)
    try:
        return await agent.handle_approval(req.approval_id, req.approved, req.reason)
    except LLMNotConfigured as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
