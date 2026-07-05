"""
Unified LLM client interface with Groq implementation.

Provides a clean, type-safe abstraction over the Groq API for use
across all agentic pattern implementations.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from typing import Any, Optional

from dotenv import load_dotenv
from groq import AsyncGroq

load_dotenv()

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "llama-3.3-70b-versatile"
FAST_MODEL = "llama-3.1-8b-instant"


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


@dataclass
class Message:
    """A single chat message."""

    role: str  # "system" | "user" | "assistant" | "tool"
    content: str
    tool_call_id: Optional[str] = None       # required when role == "tool"
    tool_calls: Optional[list[dict]] = None  # raw tool_calls for assistant replay

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {"role": self.role, "content": self.content}
        if self.tool_call_id:
            d["tool_call_id"] = self.tool_call_id
        if self.tool_calls:
            d["tool_calls"] = self.tool_calls
        return d


@dataclass
class ToolCall:
    """A tool invocation requested by the LLM."""

    id: str
    name: str
    arguments: dict[str, Any]


@dataclass
class LLMResponse:
    """A response from the LLM."""

    content: str
    model: str
    tool_calls: list[ToolCall] = field(default_factory=list)
    raw_tool_calls: list[dict] = field(default_factory=list)  # for assistant message replay
    prompt_tokens: int = 0
    completion_tokens: int = 0

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens

    @property
    def has_tool_calls(self) -> bool:
        return len(self.tool_calls) > 0

    def as_assistant_message(self) -> Message:
        """Return an assistant Message that faithfully replays this response."""
        return Message(
            role="assistant",
            content=self.content or "",
            tool_calls=self.raw_tool_calls if self.raw_tool_calls else None,
        )


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class LLMError(Exception):
    """Raised when an LLM API call fails."""


class LLMConfigError(LLMError):
    """Raised for configuration issues (missing API key, etc.)."""


class LLMRateLimitError(LLMError):
    """Raised when the API rate limit is exceeded."""


class LLMTimeoutError(LLMError):
    """Raised when the API request times out."""


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------


class GroqClient:
    """
    Async Groq LLM client with a clean, unified interface.

    All pattern classes share a single instance of this client.

    Example::

        client = GroqClient()
        response = await client.complete(
            messages=[Message(role="user", content="Hello!")],
        )
        print(response.content)
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = DEFAULT_MODEL,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> None:
        key = api_key or os.getenv("GROQ_API_KEY")
        if not key:
            raise LLMConfigError(
                "GROQ_API_KEY not found. "
                "Set it as an environment variable or pass api_key=... to GroqClient()."
            )
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self._client = AsyncGroq(api_key=key)
        logger.debug("GroqClient initialised (model=%s)", model)

    async def complete(
        self,
        messages: list[Message],
        *,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        tools: Optional[list[dict[str, Any]]] = None,
    ) -> LLMResponse:
        """
        Send a list of messages to the LLM and return the response.

        Args:
            messages:    Conversation history as ``Message`` objects.
            model:       Override the default model for this call.
            temperature: Override the default temperature for this call.
            max_tokens:  Override the default max_tokens for this call.
            tools:       OpenAI-style tool/function definitions for tool use.

        Returns:
            ``LLMResponse`` with content, token counts, and any tool calls.

        Raises:
            LLMError:          On general API failure.
            LLMRateLimitError: On HTTP 429 / rate limit exceeded.
            LLMTimeoutError:   On request timeout.
        """
        payload: dict[str, Any] = {
            "model": model or self.model,
            "messages": [m.to_dict() for m in messages],
            "temperature": temperature if temperature is not None else self.temperature,
            "max_tokens": max_tokens or self.max_tokens,
        }
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"

        logger.debug(
            "Sending request to Groq (model=%s, messages=%d)",
            payload["model"],
            len(messages),
        )

        try:
            response = await self._client.chat.completions.create(**payload)
        except Exception as exc:
            msg = str(exc)
            logger.error("Groq API call failed: %s", msg)
            if "429" in msg or "rate_limit" in msg.lower():
                raise LLMRateLimitError(f"Rate limit exceeded: {exc}") from exc
            if "timeout" in msg.lower():
                raise LLMTimeoutError(f"Request timed out: {exc}") from exc
            raise LLMError(f"Groq API request failed: {exc}") from exc

        choice = response.choices[0]
        message = choice.message

        tool_calls: list[ToolCall] = []
        raw_tool_calls: list[dict] = []

        if message.tool_calls:
            for tc in message.tool_calls:
                try:
                    args = json.loads(tc.function.arguments)
                except json.JSONDecodeError:
                    args = {}
                tool_calls.append(
                    ToolCall(id=tc.id, name=tc.function.name, arguments=args)
                )
                raw_tool_calls.append(
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        },
                    }
                )

        return LLMResponse(
            content=message.content or "",
            model=response.model,
            tool_calls=tool_calls,
            raw_tool_calls=raw_tool_calls,
            prompt_tokens=response.usage.prompt_tokens,
            completion_tokens=response.usage.completion_tokens,
        )

    async def complete_text(
        self,
        prompt: str,
        *,
        system: Optional[str] = None,
        **kwargs: Any,
    ) -> str:
        """
        Convenience wrapper: send a single user prompt and return plain text.

        Args:
            prompt: The user message.
            system: Optional system instruction.
            **kwargs: Forwarded to ``complete()``.

        Returns:
            The assistant's text reply.
        """
        messages: list[Message] = []
        if system:
            messages.append(Message(role="system", content=system))
        messages.append(Message(role="user", content=prompt))
        response = await self.complete(messages, **kwargs)
        return response.content
