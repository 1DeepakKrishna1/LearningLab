"""Intent Alignment Verification guardrail (sequence_id = 32)."""
from __future__ import annotations

from typing import List

from guardrails.base.guardrail import InputGuardrail
from guardrails.llm.client import LLMMessage, parse_llm_json
from guardrails.models.types import GuardrailConfig, GuardrailResult, PipelineContext

_LLM_SYSTEM_PROMPT = """\
You are an intent classifier for an AI assistant. Classify the user's intent from the input.
Respond ONLY with valid JSON:
{{"result": "pass"|"fail",
  "score": float (0.0–1.0, 1.0 = fully aligned with allowed intents),
  "detected_intent": str,
  "reason": str,
  "flags": [str]}}"""

_DEFAULT_INTENTS = [
    "question_answering",
    "summarization",
    "code_generation",
    "analysis",
    "creative_writing",
    "data_extraction",
    "translation",
    "planning",
]


class IntentAlignmentGuardrail(InputGuardrail):
    """Verifies that the user's intent is among the allowed intents.

    Requires an LLM client; returns SKIP gracefully if none is configured.

    Parameters:
        allowed_intents (list[str]): Whitelist of acceptable intent labels.
        use_llm (bool, default True): Must be True for this guardrail to run.
    """

    def __init__(self, config: GuardrailConfig, **kwargs) -> None:
        super().__init__(config, **kwargs)
        self._allowed: List[str] = config.parameters.get(
            "allowed_intents", _DEFAULT_INTENTS
        )
        self._use_llm: bool = config.parameters.get("use_llm", True)

    async def _execute(self, content: str, context: PipelineContext) -> GuardrailResult:
        if not self._use_llm or self.llm_client is None:
            return self._skip_result("LLM client not configured for intent alignment")

        allowed_str = ", ".join(self._allowed)
        messages = [
            LLMMessage(role="system", content=_LLM_SYSTEM_PROMPT),
            LLMMessage(
                role="user",
                content=(
                    f"Allowed intents: {allowed_str}\n\n"
                    f"Classify the following input:\n{content}"
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
        detected: str = data.get("detected_intent", "unknown")
        reason: str = data.get("reason", "")
        flags: list = data.get("flags", [])

        context.metadata["detected_intent"] = detected

        if result_label == "fail" or score < self.config.threshold:
            return self._fail_result(
                score=score,
                message=f"Intent '{detected}' not in allowed list. {reason}",
                flags=flags or ["INTENT_MISMATCH"],
            )
        return self._pass_result(
            score=score,
            message=f"Intent '{detected}' is aligned. {reason}",
        )
