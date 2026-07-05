"""Groq LLM integration. Provides a generic, stage-aware AI assist used across
every system. AI is only invoked for a stage when the SystemAdmin has enabled it."""
from __future__ import annotations

import httpx
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import AIInvocation
from app.services.config_builder import load_catalog, stage_by_key


class AIError(Exception):
    pass


def _task_system_prompt(task: str) -> str:
    prompts = load_catalog().get("ai_task_prompts", {})
    base = prompts.get(
        task, "You are a helpful assistant supporting an allocation workflow."
    )
    return (
        f"{base}\n\nYou are an assistant inside the iAlloc platform. "
        "Be accurate, fair and unbiased. You ADVISE only; a human makes the final "
        "decision. Never invent facts not present in the provided context."
    )


def is_configured() -> bool:
    return bool(settings.GROQ_API_KEY)


def call_groq(messages: list[dict], model: str | None = None,
              temperature: float = 0.2) -> dict:
    """Low-level Groq chat-completions call (OpenAI-compatible)."""
    if not is_configured():
        raise AIError(
            "GROQ_API_KEY is not set. Add it to backend/.env to enable AI assistance."
        )
    model = model or settings.GROQ_DEFAULT_MODEL
    url = f"{settings.GROQ_BASE_URL}/chat/completions"
    payload = {"model": model, "messages": messages, "temperature": temperature}
    headers = {
        "Authorization": f"Bearer {settings.GROQ_API_KEY}",
        "Content-Type": "application/json",
    }
    try:
        resp = httpx.post(url, json=payload, headers=headers, timeout=60.0)
        resp.raise_for_status()
    except httpx.HTTPStatusError as exc:
        raise AIError(f"Groq API error {exc.response.status_code}: {exc.response.text}")
    except httpx.HTTPError as exc:
        raise AIError(f"Could not reach Groq: {exc}")
    data = resp.json()
    content = data["choices"][0]["message"]["content"]
    usage = data.get("usage", {})
    return {"content": content, "model": model, "tokens": usage.get("total_tokens", 0)}


def run_stage_ai(
    db: Session,
    *,
    system,
    stage_key: str,
    user_id: int | None,
    user_input: str,
    context: dict | None = None,
    override_task: str | None = None,
) -> dict:
    """Run the AI assist configured for a stage and log the invocation."""
    stage = stage_by_key(system.config or {}, stage_key)
    if stage is None:
        raise AIError(f"Stage '{stage_key}' not found in system config.")
    ai_cfg = stage.get("ai", {})
    if not ai_cfg.get("enabled") and not override_task:
        raise AIError(
            f"AI is not enabled for the '{stage.get('name', stage_key)}' stage."
        )

    task = override_task or ai_cfg.get("task") or "validate_application"
    model = ai_cfg.get("model") or None
    extra_instructions = ai_cfg.get("instructions", "")

    system_prompt = _task_system_prompt(task)
    if extra_instructions:
        system_prompt += f"\n\nAdditional instructions from the administrator:\n{extra_instructions}"

    ctx_lines = []
    if context:
        for k, v in context.items():
            ctx_lines.append(f"- {k}: {v}")
    ctx_block = ("\n\nContext:\n" + "\n".join(ctx_lines)) if ctx_lines else ""

    user_msg = f"{user_input}{ctx_block}"
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_msg},
    ]

    result = call_groq(messages, model=model)

    db.add(
        AIInvocation(
            system_id=system.id,
            stage_key=stage_key,
            task=task,
            user_id=user_id,
            model=result["model"],
            prompt=user_msg,
            response=result["content"],
            tokens=result["tokens"],
        )
    )
    db.commit()
    return {"task": task, **result}
