"""Generates analytics, summaries, and insights for a conversation."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from app.config import load_system_config
from app.models import Conversation, Message
from app.schemas import AnalyticsOut, InsightsOut, SummaryOut


def get_analytics(db: Session, conversation_id: str) -> AnalyticsOut:
    conv: Conversation | None = db.query(Conversation).filter(
        Conversation.id == conversation_id
    ).first()
    if not conv:
        raise ValueError(f"Conversation {conversation_id} not found")

    msgs: list[Message] = conv.messages

    user_msgs = [m for m in msgs if m.role == "user"]
    asst_msgs = [m for m in msgs if m.role == "assistant"]
    total_tokens = sum(m.tokens_in + m.tokens_out for m in msgs)
    total_time = sum(m.time_taken for m in asst_msgs)
    guardrail_count = sum(1 for m in msgs if m.guardrail_triggered)

    avg_tokens = total_tokens / len(asst_msgs) if asst_msgs else 0.0
    avg_time = total_time / len(asst_msgs) if asst_msgs else 0.0

    duration = 0.0
    if msgs:
        delta = (msgs[-1].created_at - msgs[0].created_at).total_seconds()
        duration = delta / 60.0

    return AnalyticsOut(
        conversation_id=conversation_id,
        username=conv.user.username,
        total_messages=len(msgs),
        user_messages=len(user_msgs),
        assistant_messages=len(asst_msgs),
        total_tokens=total_tokens,
        avg_tokens_per_response=round(avg_tokens, 1),
        avg_response_time=round(avg_time, 3),
        total_time=round(total_time, 3),
        guardrail_triggers=guardrail_count,
        session_duration_minutes=round(duration, 2),
        llm_provider=conv.llm_provider,
        created_at=conv.created_at,
    )


def _call_llm_for_analysis(prompt: str) -> str:
    """Thin wrapper to call the active LLM for meta-analysis tasks."""
    config = load_system_config()
    provider = config.get("active_llm", "openai")
    models = config.get("models", {})
    model = models.get(provider, "gpt-4o")

    from app.services.llm_service import call_llm

    result = call_llm(
        provider=provider,
        model=model,
        system_prompt="You are a concise, insightful analyst.",
        context_messages=[],
        user_query=prompt,
    )
    return result.text.strip()


def _build_transcript(msgs: list[Message]) -> str:
    return "\n".join(f"{m.role.upper()}: {m.content}" for m in msgs)


def get_summary(db: Session, conversation_id: str) -> SummaryOut:
    conv: Conversation | None = db.query(Conversation).filter(
        Conversation.id == conversation_id
    ).first()
    if not conv:
        raise ValueError(f"Conversation {conversation_id} not found")

    if not conv.messages:
        return SummaryOut(
            conversation_id=conversation_id,
            summary="No messages in this conversation.",
            generated_at=datetime.utcnow(),
        )

    transcript = _build_transcript(conv.messages)
    prompt = (
        "Provide a concise summary (5-8 sentences) of the following conversation. "
        "Include the main topics, key questions asked, and the quality of answers provided.\n\n"
        f"{transcript}"
    )

    try:
        summary_text = _call_llm_for_analysis(prompt)
    except Exception as exc:
        summary_text = f"Summary unavailable: {exc}"

    # Persist summary on the conversation
    conv.summary = summary_text
    db.commit()

    return SummaryOut(
        conversation_id=conversation_id,
        summary=summary_text,
        generated_at=datetime.utcnow(),
    )


def get_insights(db: Session, conversation_id: str) -> InsightsOut:
    conv: Conversation | None = db.query(Conversation).filter(
        Conversation.id == conversation_id
    ).first()
    if not conv:
        raise ValueError(f"Conversation {conversation_id} not found")

    if not conv.messages:
        return InsightsOut(
            conversation_id=conversation_id,
            insights=["No messages to analyse."],
            sentiment="neutral",
            topics=[],
            generated_at=datetime.utcnow(),
        )

    import json, re

    transcript = _build_transcript(conv.messages)
    prompt = (
        "Analyse the following conversation and return ONLY a JSON object with these fields:\n"
        '  "insights": [list of 3-5 actionable insight strings],\n'
        '  "sentiment": "positive" | "neutral" | "negative",\n'
        '  "topics": [list of 3-6 main topic strings]\n\n'
        f"{transcript}\n\nReturn only the JSON, no markdown fences."
    )

    insights: list[str] = []
    sentiment = "neutral"
    topics: list[str] = []

    try:
        raw = _call_llm_for_analysis(prompt)
        # Strip possible markdown fences
        raw = re.sub(r"```[a-z]*\n?", "", raw).strip()
        data = json.loads(raw)
        insights = data.get("insights", [])
        sentiment = data.get("sentiment", "neutral")
        topics = data.get("topics", [])
    except Exception as exc:
        insights = [f"Insight generation failed: {exc}"]

    return InsightsOut(
        conversation_id=conversation_id,
        insights=insights,
        sentiment=sentiment,
        topics=topics,
        generated_at=datetime.utcnow(),
    )
