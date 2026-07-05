"""
Pattern 1 – Prompt Chaining
============================
Sequential pipeline where the output of each LLM call becomes the
input for the next.  Each step refines or transforms the content,
building toward a final polished result.

Pipeline used in this demo:
  [User topic]
      ↓  Step 1: Generate a structured outline
      ↓  Step 2: Expand the outline into a draft article
      ↓  Step 3: Edit the draft for clarity and conciseness
      ↓  Step 4: Write a one-sentence headline
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from llm_client import GroqClient
from patterns.base import BasePattern


@dataclass
class ChainResult:
    topic: str
    outline: str
    draft: str
    edited: str
    headline: str


class PromptChainingPattern(BasePattern):
    """
    Demonstrates sequential prompt chaining.

    Each step receives the previous step's output as context,
    progressively refining raw input into a polished article.
    """

    name = "1 · Prompt Chaining"

    async def run(self, topic: str = "The impact of AI on software engineering") -> ChainResult:  # type: ignore[override]
        self.print_header()
        print(f"Topic: {topic}\n")

        # ── Step 1: Outline ──────────────────────────────────────────
        outline = await self.client.complete_text(
            f"Create a concise, structured outline (max 5 bullet points) for a short "
            f"technical article about: {topic}",
            system="You are a senior technical writer. Respond only with the outline.",
            max_tokens=300,
        )
        self.print_step("Step 1 › Outline", outline)

        # ── Step 2: Draft ────────────────────────────────────────────
        draft = await self.client.complete_text(
            f"Using the following outline, write a short technical article (300–400 words).\n\n"
            f"Outline:\n{outline}",
            system="You are a technical writer. Write clearly and informatively.",
            max_tokens=700,
        )
        self.print_step("Step 2 › Draft Article", draft)

        # ── Step 3: Edit ─────────────────────────────────────────────
        edited = await self.client.complete_text(
            f"Edit the following article for clarity, grammar, and conciseness. "
            f"Remove any redundancy. Return only the improved article.\n\n{draft}",
            system="You are a copy editor with a focus on technical writing.",
            max_tokens=700,
        )
        self.print_step("Step 3 › Edited Article", edited)

        # ── Step 4: Headline ─────────────────────────────────────────
        headline = await self.client.complete_text(
            f"Write a single compelling headline for this article. "
            f"Return only the headline, no punctuation at the end.\n\n{edited}",
            system="You are a headline writer for a tech publication.",
            max_tokens=60,
        )
        self.print_step("Step 4 › Headline", headline)

        result = ChainResult(
            topic=topic,
            outline=outline,
            draft=draft,
            edited=edited,
            headline=headline,
        )
        self.print_result(f'Headline: "{headline}"')
        return result
