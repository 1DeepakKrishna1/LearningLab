"""Logical Consistency Checker guardrail (sequence_id = 4)."""
from __future__ import annotations

from guardrails.base.guardrail import OutputGuardrail
from guardrails.llm.client import LLMMessage, parse_llm_json
from guardrails.models.types import GuardrailConfig, GuardrailResult, PipelineContext

_LLM_SYSTEM_PROMPT = """\
You are a logical consistency auditor. Given an original request and an AI response, check whether:
1. The response is internally consistent (no self-contradictions).
2. The response is consistent with the original request.
Respond ONLY with valid JSON:
{{"result": "pass"|"fail",
  "score": float (0.0–1.0, 1.0 = fully consistent),
  "reason": str,
  "flags": [str]}}"""


class LogicalConsistencyGuardrail(OutputGuardrail):
    """Checks internal and request-response logical consistency via LLM.

    Returns SKIP when no LLM client is provided.

    Parameters:
        use_llm (bool, default True): Enable LLM-based analysis.
    """

    def __init__(self, config: GuardrailConfig, **kwargs) -> None:
        super().__init__(config, **kwargs)
        self._use_llm: bool = config.parameters.get("use_llm", True)

    async def _execute(self, content: str, context: PipelineContext) -> GuardrailResult:
        if not self._use_llm or self.llm_client is None:
            return self._skip_result("LLM client not configured for consistency check")

        if not content.strip():
            return self._fail_result(score=0.0, message="Empty output", flags=["EMPTY"])

        messages = [
            LLMMessage(role="system", content=_LLM_SYSTEM_PROMPT),
            LLMMessage(
                role="user",
                content=(
                    f"Original request:\n{context.effective_input}\n\n"
                    f"AI response:\n{content}"
                ),
            ),
        ]
        resp = await self.llm_client.complete(
            messages,
            temperature=0.0,
            max_tokens=256,
            timeout=self.config.timeout_seconds,
        )
        data = parse_llm_json(resp.content)
        result_label: str = data.get("result", "pass")
        score: float = float(data.get("score", 1.0))
        reason: str = data.get("reason", "")
        flags: list = data.get("flags", [])

        if result_label == "fail" or score < self.config.threshold:
            return self._fail_result(
                score=score,
                message=f"Logical inconsistency: {reason}",
                flags=flags or ["INCONSISTENT"],
            )
        return self._pass_result(score=score, message=reason)
