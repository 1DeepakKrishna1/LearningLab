"""Contextual Relevance Check guardrail (sequence_id = 8)."""
from __future__ import annotations

from typing import List, Optional

from guardrails.base.guardrail import InputGuardrail
from guardrails.llm.client import LLMMessage, parse_llm_json
from guardrails.models.types import GuardrailConfig, GuardrailResult, PipelineContext

_LLM_SYSTEM_PROMPT = """\
You are a relevance classifier. Given a list of allowed topics and user input, decide whether
the input is on-topic.  Respond ONLY with valid JSON:
{{"result": "pass"|"fail", "score": float (0.0–1.0, 1.0 = fully relevant),
  "reason": str, "flags": [str]}}
If no topics are specified, always return pass with score 1.0."""


class ContextualRelevanceGuardrail(InputGuardrail):
    """Verifies that the user input is relevant to the configured domain.

    When ``allowed_topics`` is empty the check is a no-op (always PASS).
    Falls back to a simple keyword-presence check when no LLM client is set.

    Parameters:
        allowed_topics (list[str]): Domain keywords / topic labels.
        use_llm (bool, default True): Use LLM for nuanced relevance scoring.
    """

    def __init__(self, config: GuardrailConfig, **kwargs) -> None:
        super().__init__(config, **kwargs)
        self._topics: List[str] = config.parameters.get("allowed_topics", [])
        self._use_llm: bool = config.parameters.get("use_llm", True)

    async def _execute(self, content: str, context: PipelineContext) -> GuardrailResult:
        if not self._topics:
            return self._pass_result(score=1.0, message="No topic restriction configured")

        if self._use_llm and self.llm_client is not None:
            return await self._llm_check(content)

        return self._keyword_check(content)

    # ------------------------------------------------------------------
    def _keyword_check(self, content: str) -> GuardrailResult:
        lower = content.lower()
        matches = [t for t in self._topics if t.lower() in lower]
        if matches:
            return self._pass_result(
                score=len(matches) / len(self._topics),
                message=f"Relevant topics found: {', '.join(matches)}",
            )
        return self._fail_result(
            score=0.0,
            message=f"Input does not match allowed topics: {', '.join(self._topics)}",
            flags=["OFF_TOPIC"],
        )

    async def _llm_check(self, content: str) -> GuardrailResult:
        topic_list = ", ".join(self._topics)
        messages = [
            LLMMessage(role="system", content=_LLM_SYSTEM_PROMPT),
            LLMMessage(
                role="user",
                content=f"Allowed topics: {topic_list}\n\nUser input:\n{content}",
            ),
        ]
        resp = await self.llm_client.complete(
            messages,
            temperature=0.0,
            max_tokens=200,
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
                message=f"Off-topic input: {reason}",
                flags=flags or ["OFF_TOPIC"],
            )
        return self._pass_result(score=score, message=reason)
