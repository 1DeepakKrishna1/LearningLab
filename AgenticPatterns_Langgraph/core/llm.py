"""
llm.py — GroqLLMClient: unified LLM access for all patterns.

Provides:
  - self.large  : ChatGroq(llama-3.3-70b-versatile)  — reasoning-heavy tasks
  - self.small  : ChatGroq(llama3-8b-8192)            — fast classification / scoring
  - self.chat() : direct string-in / string-out completion via raw Groq SDK
  - self.chat_with_tools() : raw tool-calling via Groq SDK
"""
from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from groq import Groq
from langchain_groq import ChatGroq

load_dotenv()

MODEL_LARGE = "llama-3.3-70b-versatile"
MODEL_SMALL = "llama-3.1-8b-instant"   # llama3-8b-8192 was decommissioned Mar 2025


class GroqLLMClient:
    """Thin adapter that exposes both LangChain ChatGroq objects and a raw
    Groq SDK client so patterns can choose the most convenient interface."""

    def __init__(self, api_key: Optional[str] = None) -> None:
        self.api_key = api_key or os.getenv("GROQ_API_KEY")
        if not self.api_key:
            raise EnvironmentError(
                "GROQ_API_KEY is not set. "
                "Copy .env.example to .env and add your key."
            )
        self._raw: Groq = Groq(api_key=self.api_key)

        # LangChain-compatible ChatGroq instances (used directly in LangGraph nodes)
        self.large: ChatGroq = ChatGroq(
            model=MODEL_LARGE,
            api_key=self.api_key,
            temperature=0.7,
        )
        self.small: ChatGroq = ChatGroq(
            model=MODEL_SMALL,
            api_key=self.api_key,
            temperature=0.1,
        )

    # ------------------------------------------------------------------
    # Convenience wrappers around the raw Groq SDK
    # ------------------------------------------------------------------

    def chat(
        self,
        messages: List[Dict[str, str]],
        model: str = MODEL_LARGE,
        temperature: float = 0.7,
        max_tokens: int = 1024,
        system: Optional[str] = None,
    ) -> str:
        """Simple string-in / string-out completion.

        Args:
            messages: List of {"role": ..., "content": ...} dicts.
            model: Groq model id.
            temperature: Sampling temperature.
            max_tokens: Maximum tokens in the response.
            system: Optional system prompt prepended before messages.

        Returns:
            The assistant's reply as a plain string.
        """
        payload: List[Dict[str, str]] = []
        if system:
            payload.append({"role": "system", "content": system})
        payload.extend(messages)

        response = self._raw.chat.completions.create(
            model=model,
            messages=payload,  # type: ignore[arg-type]
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content or ""

    def chat_with_tools(
        self,
        messages: List[Dict[str, Any]],
        tools: List[Dict[str, Any]],
        model: str = MODEL_LARGE,
        tool_choice: str = "auto",
    ) -> Any:
        """Tool-calling completion via raw Groq SDK.

        Returns the raw ``ChatCompletionMessage`` so callers can inspect
        ``tool_calls`` and ``content`` directly.
        """
        response = self._raw.chat.completions.create(
            model=model,
            messages=messages,  # type: ignore[arg-type]
            tools=tools,  # type: ignore[arg-type]
            tool_choice=tool_choice,
        )
        return response.choices[0].message

    def simple_prompt(
        self,
        prompt: str,
        model: str = MODEL_LARGE,
        temperature: float = 0.7,
        max_tokens: int = 1024,
    ) -> str:
        """Single-turn convenience helper — wraps *prompt* as a user message."""
        return self.chat(
            messages=[{"role": "user", "content": prompt}],
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
        )
