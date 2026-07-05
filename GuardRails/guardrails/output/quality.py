"""Output Quality Assessment guardrail (sequence_id = 32)."""
from __future__ import annotations

from guardrails.base.guardrail import OutputGuardrail
from guardrails.llm.client import LLMMessage, parse_llm_json
from guardrails.models.types import GuardrailConfig, GuardrailResult, PipelineContext

_LLM_SYSTEM_PROMPT = """\
You are a quality evaluator for AI-generated responses. Assess the response on:
- Completeness (does it fully address the request?)
- Accuracy (is the information plausible and correct?)
- Helpfulness (is it actionable and useful?)
- Clarity (is it well-structured and easy to understand?)
Respond ONLY with valid JSON:
{{"result": "pass"|"fail",
  "score": float (0.0–1.0, 1.0 = perfect quality),
  "dimensions": {{"completeness": float, "accuracy": float, "helpfulness": float, "clarity": float}},
  "reason": str,
  "flags": [str]}}"""


class OutputQualityGuardrail(OutputGuardrail):
    """Holistic LLM-based quality assessment of the generated output.

    Returns SKIP when no LLM client is provided.

    Parameters:
        use_llm (bool, default True): Enable LLM-based quality scoring.
        min_quality_score (float, default 0.5): Minimum composite score to pass.
    """

    def __init__(self, config: GuardrailConfig, **kwargs) -> None:
        super().__init__(config, **kwargs)
        self._use_llm: bool = config.parameters.get("use_llm", True)
        self._min_score: float = config.parameters.get("min_quality_score", 0.5)

    async def _execute(self, content: str, context: PipelineContext) -> GuardrailResult:
        if not self._use_llm or self.llm_client is None:
            return self._skip_result("LLM client not configured for quality assessment")

        if not content.strip():
            return self._fail_result(score=0.0, message="Empty output", flags=["EMPTY"])

        messages = [
            LLMMessage(role="system", content=_LLM_SYSTEM_PROMPT),
            LLMMessage(
                role="user",
                content=(
                    f"Original request:\n{context.effective_input}\n\n"
                    f"AI response to evaluate:\n{content}"
                ),
            ),
        ]
        resp = await self.llm_client.complete(
            messages,
            temperature=0.0,
            max_tokens=300,
            timeout=self.config.timeout_seconds,
        )
        data = parse_llm_json(resp.content)
        result_label: str = data.get("result", "pass")
        score: float = float(data.get("score", 1.0))
        reason: str = data.get("reason", "")
        flags: list = data.get("flags", [])
        dimensions: dict = data.get("dimensions", {})

        context.metadata["quality_dimensions"] = dimensions

        if result_label == "fail" or score < self._min_score:
            return self._fail_result(
                score=score,
                message=f"Quality below threshold ({score:.2f} < {self._min_score}): {reason}",
                flags=flags or ["LOW_QUALITY"],
            )
        return self._pass_result(score=score, message=f"Quality score {score:.2f}: {reason}")
