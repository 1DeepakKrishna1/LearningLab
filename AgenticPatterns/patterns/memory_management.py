"""
Pattern 8 – Memory Management
================================
Agents maintain state across multiple turns using two complementary
memory stores:

  Short-term memory  – a bounded conversation buffer (sliding window)
                       that keeps the last N message pairs in context.

  Long-term memory   – a persistent key-value store of distilled facts
                       extracted from the conversation.  The agent
                       proactively reads from it at the start of each
                       turn and writes new facts after each reply.

Memory lifecycle in this demo:
  Turn 1: user shares personal facts → agent stores them in LTM
  Turn 2: user asks a question requiring memory → agent retrieves & uses facts
  Turn 3: user asks a follow-up → agent uses both STM + LTM
  Summary: agent shows what it remembers
"""

from __future__ import annotations

import json
import logging
import textwrap
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

from llm_client import GroqClient, Message
from patterns.base import BasePattern

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Memory stores
# ---------------------------------------------------------------------------


@dataclass
class MemoryEntry:
    """A single long-term memory fact."""

    key: str
    value: str
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def __str__(self) -> str:
        return f"[{self.key}] {self.value}"


class ShortTermMemory:
    """
    A rolling conversation buffer capped at ``max_pairs`` exchanges.

    Older exchanges are silently discarded when the cap is reached,
    keeping the most recent context always available.
    """

    def __init__(self, max_pairs: int = 5) -> None:
        self._buffer: deque[tuple[str, str]] = deque(maxlen=max_pairs)

    def add(self, user: str, assistant: str) -> None:
        self._buffer.append((user, assistant))

    def to_messages(self) -> list[Message]:
        msgs: list[Message] = []
        for user, assistant in self._buffer:
            msgs.append(Message(role="user", content=user))
            msgs.append(Message(role="assistant", content=assistant))
        return msgs

    @property
    def size(self) -> int:
        return len(self._buffer)


class LongTermMemory:
    """
    An in-memory key-value store of distilled facts.

    In production this would be backed by a vector database or
    persistent storage (Redis, SQLite, etc.).
    """

    def __init__(self) -> None:
        self._store: dict[str, MemoryEntry] = {}

    def store(self, key: str, value: str) -> None:
        self._store[key] = MemoryEntry(key=key, value=value)
        logger.debug("LTM stored: [%s] = %s", key, value)

    def retrieve_all(self) -> list[MemoryEntry]:
        return list(self._store.values())

    def retrieve(self, key: str) -> Optional[MemoryEntry]:
        return self._store.get(key)

    def as_context_string(self) -> str:
        if not self._store:
            return "No long-term memories stored yet."
        return "\n".join(str(e) for e in self._store.values())

    def __len__(self) -> int:
        return len(self._store)


# ---------------------------------------------------------------------------
# Memory-aware agent
# ---------------------------------------------------------------------------

_SYSTEM = """\
You are a helpful personal assistant with two types of memory:

1. SHORT-TERM MEMORY: recent conversation turns (provided as prior messages).
2. LONG-TERM MEMORY: distilled key facts recalled from previous sessions.

At the end of your response, if you learned any new, important facts about the
user (name, preferences, goals, relationships, schedule, etc.), output them as
a JSON block in this exact format (omit if nothing new was learned):

```memory
{"key": "fact_key", "value": "fact value"}
```

Use concise snake_case keys (e.g. "user_name", "preferred_language").
"""

_EXTRACTOR_SYSTEM = """\
Extract all memorable facts from the conversation turn.
Return a JSON array of {"key": ..., "value": ...} objects.
Return an empty array [] if there is nothing worth remembering.
Keys must be concise snake_case strings.
"""


class MemoryManagementPattern(BasePattern):
    """
    Demonstrates dual-layer memory management.

    The agent reads long-term memory before each turn and writes new
    facts discovered during the conversation.
    """

    name = "8 · Memory Management"

    def __init__(self, client: GroqClient) -> None:
        super().__init__(client)
        self.stm = ShortTermMemory(max_pairs=4)
        self.ltm = LongTermMemory()

    def _extract_memory_blocks(self, text: str) -> list[dict[str, str]]:
        """Parse ```memory {...} ``` blocks from an assistant reply."""
        import re

        blocks = re.findall(r"```memory\s*(\{.*?\})\s*```", text, re.DOTALL)
        facts: list[dict[str, str]] = []
        for block in blocks:
            try:
                obj = json.loads(block)
                if isinstance(obj, dict) and "key" in obj and "value" in obj:
                    facts.append(obj)
            except json.JSONDecodeError:
                pass
        return facts

    def _clean_reply(self, text: str) -> str:
        """Remove memory blocks from the visible reply."""
        import re

        return re.sub(r"```memory\s*\{.*?\}\s*```", "", text, flags=re.DOTALL).strip()

    async def _chat(self, user_message: str) -> str:
        """
        Send a user message through the memory-aware pipeline.

        1. Inject LTM context as a system note.
        2. Replay STM as prior conversation turns.
        3. Append new user message.
        4. Parse and store any new memory facts from the reply.
        5. Update STM with this exchange.
        """
        ltm_context = self.ltm.as_context_string()
        system_with_memory = (
            f"{_SYSTEM}\n\n"
            f"--- Long-Term Memory ---\n{ltm_context}\n"
            f"------------------------"
        )

        messages: list[Message] = [
            Message(role="system", content=system_with_memory),
            *self.stm.to_messages(),
            Message(role="user", content=user_message),
        ]

        response = await self.client.complete(messages, max_tokens=600)
        raw_reply = response.content

        # Extract and persist any new memory facts
        new_facts = self._extract_memory_blocks(raw_reply)
        for fact in new_facts:
            self.ltm.store(fact["key"], fact["value"])

        clean_reply = self._clean_reply(raw_reply)
        self.stm.add(user_message, clean_reply)
        return clean_reply

    async def run(self, turns: Optional[list[str]] = None) -> dict[str, Any]:  # type: ignore[override]
        self.print_header()

        if turns is None:
            turns = [
                "Hi! I'm Alex. I'm a Python developer and I love hiking.",
                "What programming language do I use and what's my hobby?",
                "I'm also learning Rust and planning a trip to Patagonia next year.",
                "Summarise everything you know about me.",
            ]

        results: list[dict[str, str]] = []

        for i, user_msg in enumerate(turns, start=1):
            self.print_step(f"Turn {i} › User", user_msg)
            reply = await self._chat(user_msg)
            self.print_step(f"Turn {i} › Assistant", reply)
            results.append({"user": user_msg, "assistant": reply})

        # Final memory state
        self.print_step(
            "Long-Term Memory Store",
            self.ltm.as_context_string(),
        )
        self.print_result(
            f"STM turns buffered: {self.stm.size}  |  LTM facts stored: {len(self.ltm)}"
        )

        return {
            "turns": results,
            "ltm": {e.key: e.value for e in self.ltm.retrieve_all()},
            "stm_size": self.stm.size,
        }
