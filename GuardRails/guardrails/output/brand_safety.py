"""Competitor Shield & Brand Safety guardrail (sequence_id = 128)."""
from __future__ import annotations

import re
from typing import List

from guardrails.base.guardrail import OutputGuardrail
from guardrails.models.types import GuardrailConfig, GuardrailResult, PipelineContext


class BrandSafetyGuardrail(OutputGuardrail):
    """Detects competitor brand mentions and enforces brand-voice guidelines.

    Parameters:
        competitors (list[str]): Competitor names/brands to flag.
        brand_name (str): Your brand's name (flagged if absent from response
            when ``require_brand_mention`` is True).
        block_on_competitor_mention (bool, default False): Fail (vs. just flag)
            when a competitor is mentioned.
        require_brand_mention (bool, default False): Fail when the brand name
            is absent from the response.
    """

    def __init__(self, config: GuardrailConfig, **kwargs) -> None:
        super().__init__(config, **kwargs)
        raw_competitors: List[str] = config.parameters.get("competitors", [])
        self._competitor_patterns: List[tuple] = [
            (name, re.compile(rf"\b{re.escape(name)}\b", re.IGNORECASE))
            for name in raw_competitors
        ]
        self._brand_name: str = config.parameters.get("brand_name", "")
        self._block_on_mention: bool = config.parameters.get(
            "block_on_competitor_mention", False
        )
        self._require_brand: bool = config.parameters.get("require_brand_mention", False)

    async def _execute(self, content: str, context: PipelineContext) -> GuardrailResult:
        if not self._competitor_patterns and not self._require_brand:
            return self._skip_result("No competitors or brand rules configured")

        flags: List[str] = []
        mentioned_competitors: List[str] = []

        for name, pattern in self._competitor_patterns:
            if pattern.search(content):
                mentioned_competitors.append(name)
                flags.append(f"COMPETITOR:{name}")

        brand_absent = (
            self._require_brand
            and self._brand_name
            and not re.search(
                rf"\b{re.escape(self._brand_name)}\b", content, re.IGNORECASE
            )
        )
        if brand_absent:
            flags.append("BRAND_MISSING")

        if not flags:
            return self._pass_result(score=1.0, message="Brand safety check passed")

        score = max(0.0, 1.0 - len(flags) * 0.25)

        if (mentioned_competitors and self._block_on_mention) or brand_absent:
            return self._fail_result(
                score=score,
                message=f"Brand safety issues: {', '.join(flags)}",
                flags=flags,
            )

        # Flag-only (not blocking)
        return self._pass_result(
            score=score,
            message=f"Brand safety warnings: {', '.join(flags)}",
        )
