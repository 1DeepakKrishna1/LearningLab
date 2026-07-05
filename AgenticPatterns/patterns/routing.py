"""
Pattern 2 – Routing
====================
A classifier LLM call determines the category of the user's query,
then the request is dispatched to a specialist prompt handler that is
best suited for that category.

Route map used in this demo:
  "technical"   → detailed, precise technical explanation
  "creative"    → imaginative, narrative response
  "analytical"  → structured analysis with pros/cons
  "general"     → friendly, conversational reply
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from llm_client import GroqClient, FAST_MODEL
from patterns.base import BasePattern

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Route definitions
# ---------------------------------------------------------------------------

_ROUTES: dict[str, str] = {
    "technical": (
        "You are a senior software engineer. Provide a precise, technically accurate "
        "explanation with concrete examples and code snippets where relevant."
    ),
    "creative": (
        "You are a creative writer with a vivid imagination. Craft an engaging, "
        "narrative-driven response that captivates the reader."
    ),
    "analytical": (
        "You are a strategic analyst. Structure your response with clear sections: "
        "Overview, Key Insights, Pros & Cons, and Recommendation."
    ),
    "general": (
        "You are a knowledgeable, friendly assistant. Give a clear, conversational "
        "answer that is easy to understand."
    ),
}

_CLASSIFIER_SYSTEM = (
    "You are a query classifier. Classify the user query into exactly one of these "
    "categories: technical, creative, analytical, general.\n"
    "Respond with only the category name in lowercase."
)


@dataclass
class RouteResult:
    query: str
    route: str
    response: str


class RoutingPattern(BasePattern):
    """
    Demonstrates intelligent routing.

    A lightweight classifier model categorises the query, then a
    specialist system prompt handles the response.
    """

    name = "2 · Routing"

    async def run(self, query: str = "Explain how transformer neural networks work") -> RouteResult:  # type: ignore[override]
        self.print_header()
        print(f"Query: {query}\n")

        # ── Step 1: Classify ─────────────────────────────────────────
        raw_route = await self.client.complete_text(
            query,
            system=_CLASSIFIER_SYSTEM,
            model=FAST_MODEL,       # fast model is sufficient for classification
            temperature=0.0,        # deterministic classification
            max_tokens=10,
        )
        route = raw_route.strip().lower()

        # Guard against unexpected output
        if route not in _ROUTES:
            logger.warning("Classifier returned unknown route %r – defaulting to 'general'", route)
            route = "general"

        self.print_step("Step 1 › Classifier", f"Detected category: {route!r}")

        # ── Step 2: Specialist response ───────────────────────────────
        specialist_system = _ROUTES[route]
        response = await self.client.complete_text(
            query,
            system=specialist_system,
            max_tokens=600,
        )
        self.print_step(f"Step 2 › Specialist ({route})", response)

        result = RouteResult(query=query, route=route, response=response)
        self.print_result(f"Routed to: {route}")
        return result
