"""Language Toxicity Detection guardrail (sequence_id = 4)."""
from __future__ import annotations

import json
import re
from typing import List, Optional

from guardrails.base.guardrail import InputGuardrail
from guardrails.llm.client import LLMMessage, parse_llm_json
from guardrails.models.types import GuardrailConfig, GuardrailResult, PipelineContext

# Category → compiled word-boundary patterns (non-explicit; configurable via parameters)
_DEFAULT_PATTERNS: dict = {
    "HATE_SPEECH": [
        re.compile(r"\b(hate|despise)\s+(all\s+)?(people\s+of|those)\b", re.IGNORECASE),
        re.compile(r"\bkill\s+all\s+\w+\b", re.IGNORECASE),
        re.compile(r"\b(inferior|subhuman)\s+(race|group|people)\b", re.IGNORECASE),
    ],
    "SEVERE_THREAT": [
        re.compile(r"\b(i\s+will|i'm\s+going\s+to)\s+(kill|murder|destroy)\s+(you|them|him|her)\b", re.IGNORECASE),
        re.compile(r"\b(bomb|attack|shoot)\s+(the|a|this)\s+\w+(building|school|office|place)\b", re.IGNORECASE),
    ],
    "SELF_HARM": [
        re.compile(r"\b(how\s+to|ways\s+to)\s+(commit\s+suicide|self[\s\-]harm|hurt\s+myself)\b", re.IGNORECASE),
    ],
}

_LLM_SYSTEM_PROMPT = """You are a toxicity classifier. Analyse the text and respond ONLY with valid JSON.
Schema: {"result": "pass"|"fail", "score": float (0.0=clean, 1.0=very toxic), "reason": str, "flags": [str]}
A score below 0.5 should be "pass". Be conservative — only fail obvious toxicity."""


class ToxicityGuardrail(InputGuardrail):
    """Detects toxic, hateful, or threatening language.

    Uses compiled regex patterns by default.  When ``use_llm`` is True and an
    LLM client is provided, an additional LLM-based pass is performed.

    Parameters:
        use_llm (bool, default False): Enable LLM-backed scoring.
        extra_patterns (dict[str, list[str]]): Additional regex strings keyed
            by category name.
    """

    def __init__(self, config: GuardrailConfig, **kwargs) -> None:
        super().__init__(config, **kwargs)
        self._use_llm: bool = config.parameters.get("use_llm", False)
        self._patterns = dict(_DEFAULT_PATTERNS)

        for category, raw_patterns in config.parameters.get("extra_patterns", {}).items():
            self._patterns.setdefault(category, []).extend(
                re.compile(p, re.IGNORECASE) for p in raw_patterns
            )

    async def _execute(self, content: str, context: PipelineContext) -> GuardrailResult:
        hits: List[str] = []
        for category, patterns in self._patterns.items():
            for pattern in patterns:
                if pattern.search(content):
                    hits.append(category)
                    break

        if hits:
            return self._fail_result(
                score=0.0,
                message=f"Toxic content detected: {', '.join(hits)}",
                flags=hits,
            )

        if self._use_llm and self.llm_client is not None:
            return await self._llm_check(content, context)

        return self._pass_result(score=1.0, message="No toxicity detected")

    async def _llm_check(
        self, content: str, context: PipelineContext
    ) -> GuardrailResult:
        messages = [
            LLMMessage(role="system", content=_LLM_SYSTEM_PROMPT),
            LLMMessage(role="user", content=f"Text to analyse:\n{content}"),
        ]
        resp = await self.llm_client.complete(
            messages,
            temperature=0.0,
            max_tokens=200,
            timeout=self.config.timeout_seconds,
        )
        data = parse_llm_json(resp.content)
        result_label: str = data.get("result", "pass")
        score: float = float(data.get("score", 0.5))
        reason: str = data.get("reason", "")
        flags: List[str] = data.get("flags", [])

        # score = toxicity level (0.0 clean → 1.0 very toxic); invert for safety score
        safety_score = 1.0 - score
        if result_label == "fail":
            return self._fail_result(
                score=safety_score,
                message=f"LLM toxicity check failed: {reason}",
                flags=flags,
            )
        return self._pass_result(score=safety_score, message=reason)
