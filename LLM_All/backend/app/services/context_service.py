"""Builds the rolling context window for a conversation.

Strategy:
  - Include the last N (default 5) user/assistant message pairs verbatim.
  - For older messages, generate a summary and pass it as a system-level
    context note so the LLM is aware of earlier parts of the conversation.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.config import load_system_config, settings
from app.models import Message


def _summarise_old_messages(messages: list[Message], provider: str, model: str) -> str:
    """Call the active LLM to summarise a list of messages."""
    if not messages:
        return ""

    transcript = "\n".join(
        f"{m.role.upper()}: {m.content}" for m in messages
    )
    prompt = (
        "Summarise the following conversation excerpt in 3-5 sentences, "
        "capturing the main topics discussed and any decisions or conclusions reached.\n\n"
        f"{transcript}"
    )

    try:
        from app.services.llm_service import call_llm

        result = call_llm(
            provider=provider,
            model=model,
            system_prompt="You are a concise summarisation assistant.",
            context_messages=[],
            user_query=prompt,
        )
        return result.text.strip()
    except Exception:
        # Fall back to a simple truncated transcript rather than crashing
        lines = transcript.split("\n")
        return " | ".join(lines[:10]) + ("..." if len(lines) > 10 else "")


def build_context(
    db: Session,
    conversation_id: str,
    window: int | None = None,
) -> tuple[list[dict], str | None]:
    """Return (recent_messages, optional_summary_of_older).

    recent_messages: list of {"role": ..., "content": ...} dicts for the LLM.
    summary: text summary of messages older than the window, or None.
    """
    config = load_system_config()
    if window is None:
        window = config.get("context_window", 5)

    all_messages: list[Message] = (
        db.query(Message)
        .filter(Message.conversation_id == conversation_id)
        .order_by(Message.created_at)
        .all()
    )

    if not all_messages:
        return [], None

    # Split into old vs recent (each pair = 1 user + 1 assistant message)
    cutoff = max(0, len(all_messages) - window * 2)
    old_messages = all_messages[:cutoff]
    recent_messages = all_messages[cutoff:]

    summary: str | None = None
    if old_messages:
        provider = config.get("active_llm", "openai")
        models = config.get("models", {})
        model = models.get(provider, "gpt-4o")
        summary = _summarise_old_messages(old_messages, provider, model)

    context = [{"role": m.role, "content": m.content} for m in recent_messages]
    return context, summary
