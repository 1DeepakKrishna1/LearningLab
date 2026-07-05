"""Anti-Prompt Injection Defense guardrail (sequence_id = 1)."""
from __future__ import annotations

import re
from typing import List, Tuple

from guardrails.base.guardrail import InputGuardrail
from guardrails.models.types import GuardrailConfig, GuardrailResult, PipelineContext

# Compiled patterns covering common injection techniques
_PATTERNS: List[Tuple[str, re.Pattern]] = [
    (
        "INSTRUCTION_OVERRIDE",
        re.compile(
            r"ignore\s+(all\s+)?(previous|prior|above)\s+(instructions?|prompts?|rules?|constraints?)",
            re.IGNORECASE,
        ),
    ),
    (
        "PERSONA_HIJACK",
        re.compile(
            r"(you\s+are\s+now|act\s+as\s+(a\s+|an\s+)?(?!helpful|assistant))\s*\w+",
            re.IGNORECASE,
        ),
    ),
    (
        "FORGET_TRAINING",
        re.compile(
            r"forget\s+(all\s+)?(previous|prior|your)\s+(instructions?|training|rules?)",
            re.IGNORECASE,
        ),
    ),
    (
        "DAN_JAILBREAK",
        re.compile(r"\bDAN\b|\bjailbreak\b|do\s+anything\s+now", re.IGNORECASE),
    ),
    (
        "PRETEND_BYPASS",
        re.compile(r"pretend\s+(you\s+(are|were)|to\s+be|you're)\s+", re.IGNORECASE),
    ),
    (
        "SAFETY_BYPASS",
        re.compile(
            r"(override|bypass|disable|remove)\s+(safety|filter|guardrail|restriction|rule)",
            re.IGNORECASE,
        ),
    ),
    (
        "SYSTEM_LEAK",
        re.compile(
            r"(print|output|show|reveal|display|repeat|echo)\s+(your\s+)?(system\s+)?(prompt|instruction|context)",
            re.IGNORECASE,
        ),
    ),
    (
        "LLAMA_INJECT",
        re.compile(r"\[\s*INST\s*\]|\[/?SYS\]", re.IGNORECASE),
    ),
    (
        "XML_INJECT",
        re.compile(r"<\s*system\s*>|<\s*/\s*system\s*>", re.IGNORECASE),
    ),
    (
        "MARKDOWN_INJECT",
        re.compile(r"###\s*(new\s+)?instruction", re.IGNORECASE),
    ),
    (
        "ROLE_PLAY_ESCAPE",
        re.compile(
            r"(in\s+this\s+scenario|for\s+the\s+purposes\s+of\s+this)\s+.{0,40}\s+(you\s+(must|will|should)\s+ignore)",
            re.IGNORECASE,
        ),
    ),
]


class AntiPromptInjectionGuardrail(InputGuardrail):
    """Detects prompt-injection attempts using a compiled pattern library.

    Parameters (via config.parameters):
        max_suspicious_patterns (int, default 1): Number of pattern hits before
            the guardrail fails (allows minor false-positives at > 1).
        redact (bool, default False): Replace matched text instead of blocking.
    """

    def __init__(self, config: GuardrailConfig, **kwargs) -> None:
        super().__init__(config, **kwargs)
        self._max_hits: int = config.parameters.get("max_suspicious_patterns", 1)
        self._redact: bool = config.parameters.get("redact", False)

    async def _execute(self, content: str, context: PipelineContext) -> GuardrailResult:
        hits: List[str] = []
        sanitized = content

        for label, pattern in _PATTERNS:
            if pattern.search(content):
                hits.append(label)
                if self._redact:
                    sanitized = pattern.sub("[REDACTED]", sanitized)

        if not hits:
            return self._pass_result(score=1.0, message="No injection patterns detected")

        score = max(0.0, 1.0 - len(hits) / len(_PATTERNS))

        if self._redact:
            return self._pass_result(
                score=score,
                message=f"Injection patterns redacted: {', '.join(hits)}",
                modified_content=sanitized,
            )

        if len(hits) >= self._max_hits:
            return self._fail_result(
                score=score,
                message=f"Prompt injection detected: {', '.join(hits)}",
                flags=hits,
            )

        return self._pass_result(
            score=score,
            message=f"Minor pattern matches (below threshold): {', '.join(hits)}",
        )
