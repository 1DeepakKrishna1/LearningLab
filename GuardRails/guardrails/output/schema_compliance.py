"""API Schema Compliance Checker guardrail (sequence_id = 2)."""
from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from guardrails.base.guardrail import OutputGuardrail
from guardrails.models.types import GuardrailConfig, GuardrailResult, PipelineContext

try:
    import jsonschema
    _JSONSCHEMA_AVAILABLE = True
except ImportError:
    _JSONSCHEMA_AVAILABLE = False


class SchemaComplianceGuardrail(OutputGuardrail):
    """Validates the LLM JSON output against a JSON Schema.

    Parameters:
        schema (dict | None): The JSON Schema to validate against.
            If None, the guardrail is skipped.
    """

    def __init__(self, config: GuardrailConfig, **kwargs) -> None:
        super().__init__(config, **kwargs)
        self._schema: Optional[Dict[str, Any]] = config.parameters.get("schema")

    async def _execute(self, content: str, context: PipelineContext) -> GuardrailResult:
        if not self._schema:
            return self._skip_result("No schema configured")

        if not _JSONSCHEMA_AVAILABLE:
            return self._skip_result("jsonschema package not installed")

        try:
            instance = json.loads(content)
        except json.JSONDecodeError:
            return self._fail_result(
                score=0.0,
                message="Cannot validate schema — output is not valid JSON",
                flags=["INVALID_JSON"],
            )

        validator = jsonschema.Draft7Validator(self._schema)
        errors: List[jsonschema.ValidationError] = list(validator.iter_errors(instance))

        if not errors:
            return self._pass_result(score=1.0, message="Schema validation passed")

        messages = [f"{e.json_path}: {e.message}" for e in errors[:5]]
        return self._fail_result(
            score=0.0,
            message=f"Schema violations ({len(errors)}): " + "; ".join(messages),
            flags=["SCHEMA_VIOLATION"],
        )
