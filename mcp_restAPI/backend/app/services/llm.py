"""Thin async wrapper around the OpenAI Chat Completions API."""
from __future__ import annotations

from functools import lru_cache
from typing import Any

from openai import AsyncOpenAI

from ..config import get_settings


class LLMNotConfigured(Exception):
    """Raised when no OpenAI API key is available."""


@lru_cache
def get_client() -> AsyncOpenAI:
    settings = get_settings()
    if not settings.openai_api_key:
        raise LLMNotConfigured(
            "OPENAI_API_KEY is not set. Add it to backend/.env (see .env.example)."
        )
    kwargs: dict[str, Any] = {"api_key": settings.openai_api_key}
    if settings.openai_base_url:
        kwargs["base_url"] = settings.openai_base_url
    return AsyncOpenAI(**kwargs)


async def chat_completion(
    messages: list[dict[str, Any]],
    tools: list[dict[str, Any]] | None = None,
    temperature: float = 0.1,
) -> Any:
    """Run one chat completion turn. Returns the first choice's message."""
    settings = get_settings()
    client = get_client()
    request: dict[str, Any] = {
        "model": settings.openai_model,
        "messages": messages,
        "temperature": temperature,
    }
    if tools:
        request["tools"] = tools
        request["tool_choice"] = "auto"
        # One tool call per turn keeps the human-approval pause/resume logic simple.
        request["parallel_tool_calls"] = False
    response = await client.chat.completions.create(**request)
    return response.choices[0].message
