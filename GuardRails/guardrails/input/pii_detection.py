"""PII Detection guardrail (sequence_id = 2)."""
from __future__ import annotations

import re
from typing import Dict, List, Tuple

from guardrails.base.guardrail import InputGuardrail
from guardrails.models.types import GuardrailConfig, GuardrailResult, PipelineContext

_PII_PATTERNS: Dict[str, re.Pattern] = {
    "EMAIL": re.compile(
        r"\b[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}\b"
    ),
    "US_PHONE": re.compile(
        r"\b(\+1[\s.\-]?)?\(?\d{3}\)?[\s.\-]?\d{3}[\s.\-]?\d{4}\b"
    ),
    "US_SSN": re.compile(r"\b\d{3}[\s\-]?\d{2}[\s\-]?\d{4}\b"),
    "CREDIT_CARD": re.compile(
        r"\b(?:\d{4}[\s\-]?){3}\d{4}\b"
    ),
    "IP_ADDRESS": re.compile(
        r"\b(?:(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\.){3}(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\b"
    ),
    "DOB": re.compile(
        r"\b(?:0[1-9]|1[0-2])[/\-](?:0[1-9]|[12]\d|3[01])[/\-](?:19|20)\d{2}\b"
    ),
    "PASSPORT": re.compile(r"\b[A-Z]{1,2}\d{6,9}\b"),
    "IBAN": re.compile(r"\b[A-Z]{2}\d{2}[A-Z0-9]{4}\d{7}(?:[A-Z0-9]{0,16})\b"),
}

_PLACEHOLDER = "[REDACTED-{label}]"


class PIIDetectionGuardrail(InputGuardrail):
    """Screens for Personally Identifiable Information (PII).

    Parameters (via config.parameters):
        mode (str): ``"fail"`` blocks the request; ``"redact"`` (default)
            replaces PII in-place and lets the pipeline continue.
        enabled_types (list[str]): Subset of PII type keys to check.
            Defaults to all types.
    """

    def __init__(self, config: GuardrailConfig, **kwargs) -> None:
        super().__init__(config, **kwargs)
        self._mode: str = config.parameters.get("mode", "redact")
        enabled: List[str] = config.parameters.get("enabled_types", list(_PII_PATTERNS.keys()))
        self._patterns: Dict[str, re.Pattern] = {
            k: v for k, v in _PII_PATTERNS.items() if k in enabled
        }

    async def _execute(self, content: str, context: PipelineContext) -> GuardrailResult:
        found: List[str] = []
        sanitized = content

        for label, pattern in self._patterns.items():
            if pattern.search(content):
                found.append(label)
                if self._mode == "redact":
                    sanitized = pattern.sub(_PLACEHOLDER.format(label=label), sanitized)

        if not found:
            return self._pass_result(score=1.0, message="No PII detected")

        score = max(0.0, 1.0 - len(found) / len(self._patterns))

        if self._mode == "redact":
            return self._pass_result(
                score=score,
                message=f"PII redacted: {', '.join(found)}",
                modified_content=sanitized,
            )

        return self._fail_result(
            score=score,
            message=f"PII detected: {', '.join(found)}",
            flags=found,
        )
