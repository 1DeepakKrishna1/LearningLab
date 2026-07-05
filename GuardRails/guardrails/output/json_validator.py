"""Structured Data / JSON Validator guardrail (sequence_id = 1)."""
from __future__ import annotations

import json
from typing import Any, Optional

from guardrails.base.guardrail import OutputGuardrail
from guardrails.models.types import GuardrailConfig, GuardrailResult, PipelineContext


def _looks_like_json(text: str) -> bool:
    stripped = text.strip()
    return (stripped.startswith("{") and stripped.endswith("}")) or (
        stripped.startswith("[") and stripped.endswith("]")
    )


class JSONValidatorGuardrail(OutputGuardrail):
    """Validates that the LLM output is well-formed JSON when expected.

    Parameters:
        required (bool, default False): If False, the check is skipped for
            responses that do not look like JSON.  Set to True to always
            require valid JSON output.
    """

    def __init__(self, config: GuardrailConfig, **kwargs) -> None:
        super().__init__(config, **kwargs)
        self._required: bool = config.parameters.get("required", False)

    async def _execute(self, content: str, context: PipelineContext) -> GuardrailResult:
        if not content.strip():
            return self._fail_result(score=0.0, message="Output is empty", flags=["EMPTY_OUTPUT"])

        if not self._required and not _looks_like_json(content):
            return self._skip_result("Output is not JSON — validation skipped")

        try:
            parsed: Any = json.loads(content)
        except json.JSONDecodeError as exc:
            return self._fail_result(
                score=0.0,
                message=f"Invalid JSON: {exc.msg} at line {exc.lineno}, col {exc.colno}",
                flags=["INVALID_JSON"],
            )

        context.metadata["parsed_json"] = parsed
        return self._pass_result(score=1.0, message="Valid JSON")
