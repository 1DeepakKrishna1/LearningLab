"""Abstract LLM client interface."""
from __future__ import annotations

import abc
import json
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class LLMMessage:
    role: str  # "system" | "user" | "assistant"
    content: str


@dataclass
class LLMResponse:
    content: str
    model: str
    usage: Dict[str, int] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


class LLMClient(abc.ABC):
    """Provider-agnostic interface every LLM backend must implement."""

    @abc.abstractmethod
    async def complete(
        self,
        messages: List[LLMMessage],
        *,
        temperature: float = 0.0,
        max_tokens: int = 512,
        timeout: float = 10.0,
    ) -> LLMResponse:
        """Send a chat-completion request and return the response."""

    @abc.abstractmethod
    async def health_check(self) -> bool:
        """Return True if the LLM service is reachable."""


# ---------------------------------------------------------------------------
# Shared utility used by all LLM-based guardrails
# ---------------------------------------------------------------------------

_CODE_BLOCK_RE = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL)


def parse_llm_json(text: str) -> Dict[str, Any]:
    """Extract and parse the first JSON object from an LLM response string.

    Handles markdown code fences and leading/trailing prose.
    """
    text = text.strip()
    match = _CODE_BLOCK_RE.search(text)
    if match:
        text = match.group(1).strip()

    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end > start:
        text = text[start : end + 1]

    return json.loads(text)
