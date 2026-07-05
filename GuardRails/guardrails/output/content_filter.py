"""Inappropriate Content Filter guardrail (sequence_id = 64)."""
from __future__ import annotations

import re
from typing import Dict, List

from guardrails.base.guardrail import OutputGuardrail
from guardrails.models.types import GuardrailConfig, GuardrailResult, PipelineContext

# Default patterns per category.  Extend or replace via config.parameters["extra_patterns"].
_DEFAULT_CATEGORY_PATTERNS: Dict[str, List[re.Pattern]] = {
    "HATE_SPEECH": [
        re.compile(r"\b(racial slur placeholder|ethnic hate)\b", re.IGNORECASE),
        re.compile(r"\bkill\s+all\s+\w+\b", re.IGNORECASE),
    ],
    "GRAPHIC_VIOLENCE": [
        re.compile(
            r"\b(step[\-\s]by[\-\s]step\s+instructions?\s+to\s+(kill|murder|torture))\b",
            re.IGNORECASE,
        ),
    ],
    "SELF_HARM_PROMOTION": [
        re.compile(
            r"\b(best\s+way|how\s+to)\s+(commit\s+suicide|self[\-\s]harm|hurt\s+yourself)\b",
            re.IGNORECASE,
        ),
    ],
    "ILLEGAL_ACTIVITY": [
        re.compile(
            r"\b(how\s+to\s+(make|synthesize|manufacture)\s+(meth|fentanyl|explosives|drugs))\b",
            re.IGNORECASE,
        ),
    ],
}


class ContentFilterGuardrail(OutputGuardrail):
    """Screens LLM output for inappropriate or harmful content.

    Parameters:
        categories (list[str]): Subset of category keys to enable.
            Defaults to all built-in categories.
        extra_patterns (dict[str, list[str]]): Additional regex strings keyed
            by category name.
    """

    def __init__(self, config: GuardrailConfig, **kwargs) -> None:
        super().__init__(config, **kwargs)
        enabled: List[str] = config.parameters.get(
            "categories", list(_DEFAULT_CATEGORY_PATTERNS.keys())
        )
        self._patterns: Dict[str, List[re.Pattern]] = {
            k: v for k, v in _DEFAULT_CATEGORY_PATTERNS.items() if k in enabled
        }
        for category, raw in config.parameters.get("extra_patterns", {}).items():
            self._patterns.setdefault(category, []).extend(
                re.compile(p, re.IGNORECASE) for p in raw
            )

    async def _execute(self, content: str, context: PipelineContext) -> GuardrailResult:
        hits: List[str] = []
        for category, patterns in self._patterns.items():
            for pattern in patterns:
                if pattern.search(content):
                    hits.append(category)
                    break

        if not hits:
            return self._pass_result(score=1.0, message="No inappropriate content detected")

        return self._fail_result(
            score=0.0,
            message=f"Inappropriate content detected: {', '.join(hits)}",
            flags=hits,
        )
