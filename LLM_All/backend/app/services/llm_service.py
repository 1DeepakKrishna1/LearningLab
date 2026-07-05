"""Multi-provider LLM service with a unified interface."""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from app.config import settings


@dataclass
class LLMResult:
    text: str
    tokens_in: int
    tokens_out: int
    follow_ups: list[dict[str, str]]


_FOLLOW_UP_INSTRUCTION = """
After your main response, add a JSON block at the very end (delimited by ```json and ```) containing 3 follow-up questions the user might find relevant. Format:
```json
{"follow_ups": [{"text": "Short label", "query": "Full question to ask?"}, ...]}
```
"""


def _extract_follow_ups(raw_text: str) -> tuple[str, list[dict[str, str]]]:
    """Split the LLM output into answer text and follow-up list."""
    import re

    pattern = r"```json\s*(\{.*?\})\s*```"
    match = re.search(pattern, raw_text, re.DOTALL)
    follow_ups: list[dict[str, str]] = []
    if match:
        try:
            data = json.loads(match.group(1))
            follow_ups = data.get("follow_ups", [])
        except json.JSONDecodeError:
            pass
        clean_text = raw_text[: match.start()].rstrip()
    else:
        clean_text = raw_text
    return clean_text, follow_ups


def _build_messages(
    system_prompt: str,
    context_messages: list[dict],
    user_query: str,
) -> list[dict]:
    messages: list[dict] = []
    for m in context_messages:
        messages.append({"role": m["role"], "content": m["content"]})
    messages.append({"role": "user", "content": user_query + _FOLLOW_UP_INSTRUCTION})
    return messages


# ── OpenAI ────────────────────────────────────────────────────────────────────

def _call_openai(
    model: str,
    system_prompt: str,
    context_messages: list[dict],
    user_query: str,
) -> LLMResult:
    from openai import OpenAI

    api_key = settings.get_api_key("openai")
    if not api_key:
        raise ValueError("OpenAI API key not configured")

    client = OpenAI(api_key=api_key)
    messages = _build_messages(system_prompt, context_messages, user_query)

    resp = client.chat.completions.create(
        model=model,
        messages=[{"role": "system", "content": system_prompt}] + messages,
        temperature=0.7,
        max_tokens=2048,
    )
    raw = resp.choices[0].message.content or ""
    text, follow_ups = _extract_follow_ups(raw)
    usage = resp.usage
    return LLMResult(
        text=text,
        tokens_in=usage.prompt_tokens if usage else 0,
        tokens_out=usage.completion_tokens if usage else 0,
        follow_ups=follow_ups,
    )


# ── Anthropic ─────────────────────────────────────────────────────────────────

def _call_anthropic(
    model: str,
    system_prompt: str,
    context_messages: list[dict],
    user_query: str,
) -> LLMResult:
    import anthropic

    api_key = settings.get_api_key("anthropic")
    if not api_key:
        raise ValueError("Anthropic API key not configured")

    client = anthropic.Anthropic(api_key=api_key)
    messages = _build_messages(system_prompt, context_messages, user_query)

    resp = client.messages.create(
        model=model,
        max_tokens=2048,
        system=system_prompt,
        messages=messages,
    )
    raw = resp.content[0].text if resp.content else ""
    text, follow_ups = _extract_follow_ups(raw)
    return LLMResult(
        text=text,
        tokens_in=resp.usage.input_tokens,
        tokens_out=resp.usage.output_tokens,
        follow_ups=follow_ups,
    )


# ── Google Gemini ─────────────────────────────────────────────────────────────

def _call_google(
    model: str,
    system_prompt: str,
    context_messages: list[dict],
    user_query: str,
) -> LLMResult:
    import google.generativeai as genai

    api_key = settings.get_api_key("google")
    if not api_key:
        raise ValueError("Google API key not configured")

    genai.configure(api_key=api_key)
    gen_model = genai.GenerativeModel(
        model_name=model,
        system_instruction=system_prompt,
    )

    history = []
    for m in context_messages:
        role = "user" if m["role"] == "user" else "model"
        history.append({"role": role, "parts": [m["content"]]})

    chat = gen_model.start_chat(history=history)
    resp = chat.send_message(user_query + _FOLLOW_UP_INSTRUCTION)
    raw = resp.text or ""
    text, follow_ups = _extract_follow_ups(raw)

    tokens_in = 0
    tokens_out = 0
    try:
        tokens_in = resp.usage_metadata.prompt_token_count or 0
        tokens_out = resp.usage_metadata.candidates_token_count or 0
    except Exception:
        pass

    return LLMResult(text=text, tokens_in=tokens_in, tokens_out=tokens_out, follow_ups=follow_ups)


# ── Groq (Llama / Mixtral) ────────────────────────────────────────────────────

def _call_groq(
    model: str,
    system_prompt: str,
    context_messages: list[dict],
    user_query: str,
) -> LLMResult:
    from groq import Groq

    api_key = settings.get_api_key("groq")
    if not api_key:
        raise ValueError("Groq API key not configured")

    client = Groq(api_key=api_key)
    messages = _build_messages(system_prompt, context_messages, user_query)

    resp = client.chat.completions.create(
        model=model,
        messages=[{"role": "system", "content": system_prompt}] + messages,
        temperature=0.7,
        max_tokens=2048,
    )
    raw = resp.choices[0].message.content or ""
    text, follow_ups = _extract_follow_ups(raw)
    usage = resp.usage
    return LLMResult(
        text=text,
        tokens_in=usage.prompt_tokens if usage else 0,
        tokens_out=usage.completion_tokens if usage else 0,
        follow_ups=follow_ups,
    )


# ── Public interface ──────────────────────────────────────────────────────────

_DISPATCH: dict[str, Any] = {
    "openai": _call_openai,
    "anthropic": _call_anthropic,
    "google": _call_google,
    "groq": _call_groq,
}


def call_llm(
    provider: str,
    model: str,
    system_prompt: str,
    context_messages: list[dict],
    user_query: str,
) -> LLMResult:
    fn = _DISPATCH.get(provider)
    if fn is None:
        raise ValueError(f"Unknown LLM provider: {provider!r}")
    return fn(model, system_prompt, context_messages, user_query)
