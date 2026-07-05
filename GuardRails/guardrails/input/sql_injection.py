"""SQL Injection Prevention guardrail (sequence_id = 16)."""
from __future__ import annotations

import re
from typing import List, Tuple

from guardrails.base.guardrail import InputGuardrail
from guardrails.models.types import GuardrailConfig, GuardrailResult, PipelineContext

_SQL_PATTERNS: List[Tuple[str, re.Pattern]] = [
    ("UNION_SELECT",       re.compile(r"\bUNION\b.{0,20}\bSELECT\b", re.IGNORECASE | re.DOTALL)),
    ("SELECT_FROM",        re.compile(r"\bSELECT\b.{0,50}\bFROM\b", re.IGNORECASE | re.DOTALL)),
    ("INSERT_INTO",        re.compile(r"\bINSERT\b.{0,20}\bINTO\b", re.IGNORECASE | re.DOTALL)),
    ("DROP_TABLE",         re.compile(r"\bDROP\b.{0,20}\bTABLE\b", re.IGNORECASE | re.DOTALL)),
    ("DELETE_FROM",        re.compile(r"\bDELETE\b.{0,20}\bFROM\b", re.IGNORECASE | re.DOTALL)),
    ("UPDATE_SET",         re.compile(r"\bUPDATE\b.{0,30}\bSET\b", re.IGNORECASE | re.DOTALL)),
    ("COMMENT_SQLI",       re.compile(r"';\s*--\s*$|';\s*/\*", re.IGNORECASE | re.MULTILINE)),
    ("TAUTOLOGY",          re.compile(r"\bOR\b\s+['\"0-9]+\s*=\s*['\"0-9]+", re.IGNORECASE)),
    ("AND_TAUTOLOGY",      re.compile(r"\bAND\b\s+['\"0-9]+\s*=\s*['\"0-9]+", re.IGNORECASE)),
    ("EXEC_CALL",          re.compile(r"\b(EXEC|EXECUTE)\b\s*\(", re.IGNORECASE)),
    ("XP_CMDSHELL",        re.compile(r"\bxp_cmdshell\b", re.IGNORECASE)),
    ("TIME_BASED_BLIND",   re.compile(r"\b(SLEEP|BENCHMARK|WAITFOR\s+DELAY)\s*\(", re.IGNORECASE)),
    ("STACKED_QUERY",      re.compile(r"';\s*(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE)\b", re.IGNORECASE)),
    ("HEX_ENCODING",       re.compile(r"0x[0-9a-fA-F]{4,}", re.IGNORECASE)),
    ("CHAR_FUNCTION",      re.compile(r"\bCHAR\s*\(\s*\d+", re.IGNORECASE)),
    ("INFORMATION_SCHEMA", re.compile(r"\bINFORMATION_SCHEMA\b", re.IGNORECASE)),
]


class SQLInjectionGuardrail(InputGuardrail):
    """Detects SQL injection patterns in user input.

    Parameters:
        max_allowed_hits (int, default 0): Allow this many hits before failing
            (useful when the application legitimately discusses SQL syntax).
    """

    def __init__(self, config: GuardrailConfig, **kwargs) -> None:
        super().__init__(config, **kwargs)
        self._max_allowed: int = config.parameters.get("max_allowed_hits", 0)

    async def _execute(self, content: str, context: PipelineContext) -> GuardrailResult:
        hits: List[str] = []
        for label, pattern in _SQL_PATTERNS:
            if pattern.search(content):
                hits.append(label)

        if not hits:
            return self._pass_result(score=1.0, message="No SQL injection patterns detected")

        score = max(0.0, 1.0 - len(hits) / len(_SQL_PATTERNS))

        if len(hits) > self._max_allowed:
            return self._fail_result(
                score=score,
                message=f"SQL injection detected ({len(hits)} pattern(s)): {', '.join(hits)}",
                flags=hits,
            )

        return self._pass_result(
            score=score,
            message=f"SQL patterns present but within allowed threshold: {', '.join(hits)}",
        )
