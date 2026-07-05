"""Unified LLM resolver.

Extends the existing agents-tools-library `get_llm` (openai / anthropic / google /
ollama) with **Groq** support, while keeping a single resolution path for the agent
runtime and the AI workflow builder.

Provider selection (configuration-driven):
  1. Explicit `provider` (per-agent `provider`, or `CLAWFLOW_DEFAULT_LLM_PROVIDER`).
  2. Inferred from the model name prefix (e.g. ``groq/...`` or known Groq models).
  3. Environment fallback: if only ``GROQ_API_KEY`` is set, Groq is used; otherwise
     the library's own env priority applies.

Set in `.env`:
    CLAWFLOW_DEFAULT_LLM_PROVIDER=groq
    CLAWFLOW_DEFAULT_LLM_MODEL=llama-3.3-70b-versatile   # or GROQ_MODEL
    GROQ_API_KEY=gsk_...
"""
from __future__ import annotations

import os
from typing import Any

from .logging_setup import get_logger

logger = get_logger("llm")

DEFAULT_GROQ_MODEL = "llama-3.3-70b-versatile"

# Models that are unambiguously Groq-hosted (used for inference when no provider given).
_GROQ_HINTS = ("llama-3.3", "llama-3.1", "llama3-", "mixtral-", "gemma2-", "groq/")

# Keys the library's get_llm understands; their presence means "let the library decide".
_LIBRARY_KEYS = ("OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GEMINI_API_KEY",
                 "GOOGLE_API_KEY", "OLLAMA_MODEL")


def _is_groq(provider: str, model: str | None) -> bool:
    if provider == "groq":
        return True
    if provider:  # any other explicit provider → not groq
        return False
    m = (model or "").lower()
    if any(h in m for h in _GROQ_HINTS):
        return True
    # No provider, no telltale model: pick Groq only if it's the only key available.
    return bool(os.getenv("GROQ_API_KEY")) and not any(os.getenv(k) for k in _LIBRARY_KEYS)


def _build_groq(model: str | None, temperature: float, max_tokens: int | None) -> Any:
    from langchain_groq import ChatGroq

    name = (model or os.getenv("GROQ_MODEL") or DEFAULT_GROQ_MODEL)
    if name.lower().startswith("groq/"):
        name = name.split("/", 1)[1]
    kwargs: dict[str, Any] = {"temperature": temperature}
    if max_tokens is not None:
        kwargs["max_tokens"] = max_tokens
    return ChatGroq(model=name, **kwargs)


def resolve_chat_model(
    provider: str | None = None,
    model: str | None = None,
    temperature: float = 0.0,
    max_tokens: int | None = None,
) -> Any:
    """Return a LangChain chat model for the given provider/model.

    Raises if no provider can be resolved (no keys configured at all).
    """
    prov = (provider or "").lower().strip()

    if _is_groq(prov, model):
        return _build_groq(model, temperature, max_tokens)

    # Delegate every other provider to the library's resolver.
    try:
        from library.core.llm import get_llm

        return get_llm(model=model, provider=provider or None,
                       temperature=temperature, max_tokens=max_tokens)
    except RuntimeError:
        # Library found no configured provider — try Groq if its key exists.
        if os.getenv("GROQ_API_KEY"):
            logger.info("Falling back to Groq (only GROQ_API_KEY is configured).")
            return _build_groq(model, temperature, max_tokens)
        raise
    except Exception as exc:  # noqa: BLE001 - import/availability issues
        logger.warning("Library LLM resolver unavailable (%s); trying direct construction.", exc)
        if os.getenv("GROQ_API_KEY"):
            return _build_groq(model, temperature, max_tokens)
        from langchain_anthropic import ChatAnthropic
        return ChatAnthropic(model=model or "claude-sonnet-4-6", temperature=temperature)
