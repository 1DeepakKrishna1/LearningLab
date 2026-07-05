from __future__ import annotations

import time
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.config import load_system_config
from app.database import get_db
from app.dependencies import get_current_user
from app.models import Conversation, Message, User
from app.schemas import ChatRequest, ChatResponse, FollowUp, TokensConsumed
from app.services.context_service import build_context
from app.services.guardrails_service import check_input, check_output
from app.services.llm_service import call_llm
from app.services.logging_service import log_message

router = APIRouter()


def _get_conversation(conversation_id: str, user: User, db: Session) -> Conversation:
    conv = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    if not conv:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
    if conv.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    return conv


@router.post("/{conversation_id}/message", response_model=ChatResponse)
def send_message(
    conversation_id: str,
    body: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ChatResponse:
    conv = _get_conversation(conversation_id, current_user, db)
    config = load_system_config()

    provider = conv.llm_provider or config.get("active_llm", "openai")
    models = config.get("models", {})
    model = models.get(provider, "gpt-4o")
    system_prompt = config.get("system_prompt", "You are a helpful AI assistant.")

    user_query = body.message.strip()
    guardrail_triggered = False

    # ── Input guardrail check ─────────────────────────────────────────────────
    input_check = check_input(user_query)
    if input_check.blocked:
        guardrail_triggered = True
        log_message(
            event="guardrail_input_block",
            conversation_id=conversation_id,
            username=current_user.username,
            role="user",
            content=user_query,
            guardrail_triggered=True,
            extra={"reason": input_check.reason},
        )
        # Save the user message (blocked)
        user_msg = Message(
            conversation_id=conversation_id,
            role="user",
            content=user_query,
            guardrail_triggered=True,
        )
        db.add(user_msg)

        bot_msg = Message(
            conversation_id=conversation_id,
            role="assistant",
            content=input_check.response,
            guardrail_triggered=True,
        )
        db.add(bot_msg)
        db.commit()
        db.refresh(bot_msg)

        return ChatResponse(
            conversation_id=conversation_id,
            message_id=bot_msg.id,
            query=user_query,
            response=input_check.response,
            follow_ups=[],
            tokens_consumed=TokensConsumed(input=0, output=0, total=0),
            time_taken=0.0,
            guardrail_triggered=True,
            timestamp=datetime.utcnow(),
        )

    # ── Build context window ──────────────────────────────────────────────────
    context_messages, old_summary = build_context(db, conversation_id)

    if old_summary:
        # Prepend summary as an assistant note
        context_messages = [
            {
                "role": "assistant",
                "content": f"[Earlier conversation summary: {old_summary}]",
            }
        ] + context_messages

    # ── Call LLM ─────────────────────────────────────────────────────────────
    start = time.perf_counter()
    try:
        result = call_llm(
            provider=provider,
            model=model,
            system_prompt=system_prompt,
            context_messages=context_messages,
            user_query=user_query,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"LLM call failed: {exc}",
        )
    elapsed = round(time.perf_counter() - start, 3)

    ai_response = result.text

    # ── Output guardrail check ────────────────────────────────────────────────
    output_check = check_output(ai_response)
    if output_check.blocked:
        guardrail_triggered = True
        ai_response = output_check.response

    # ── Persist messages ──────────────────────────────────────────────────────
    user_msg = Message(
        conversation_id=conversation_id,
        role="user",
        content=user_query,
        tokens_in=result.tokens_in,
        guardrail_triggered=guardrail_triggered,
    )
    db.add(user_msg)

    bot_msg = Message(
        conversation_id=conversation_id,
        role="assistant",
        content=ai_response,
        tokens_in=result.tokens_in,
        tokens_out=result.tokens_out,
        time_taken=elapsed,
        guardrail_triggered=guardrail_triggered,
    )
    db.add(bot_msg)

    # Update conversation title from first user message
    if len(conv.messages) == 0:
        conv.title = user_query[:80] + ("…" if len(user_query) > 80 else "")

    db.commit()
    db.refresh(bot_msg)

    # ── Log ───────────────────────────────────────────────────────────────────
    log_message(
        event="chat",
        conversation_id=conversation_id,
        username=current_user.username,
        role="assistant",
        content=ai_response,
        tokens_in=result.tokens_in,
        tokens_out=result.tokens_out,
        time_taken=elapsed,
        guardrail_triggered=guardrail_triggered,
    )

    follow_ups = [FollowUp(text=f["text"], query=f["query"]) for f in result.follow_ups]

    return ChatResponse(
        conversation_id=conversation_id,
        message_id=bot_msg.id,
        query=user_query,
        response=ai_response,
        follow_ups=follow_ups,
        tokens_consumed=TokensConsumed(
            input=result.tokens_in,
            output=result.tokens_out,
            total=result.tokens_in + result.tokens_out,
        ),
        time_taken=elapsed,
        guardrail_triggered=guardrail_triggered,
        timestamp=datetime.utcnow(),
    )


@router.get("/{conversation_id}/history")
def get_history(
    conversation_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    conv = _get_conversation(conversation_id, current_user, db)
    return {
        "conversation_id": conversation_id,
        "messages": [
            {
                "id": m.id,
                "role": m.role,
                "content": m.content,
                "tokens_in": m.tokens_in,
                "tokens_out": m.tokens_out,
                "time_taken": m.time_taken,
                "guardrail_triggered": m.guardrail_triggered,
                "created_at": m.created_at.isoformat(),
            }
            for m in conv.messages
        ],
    }
