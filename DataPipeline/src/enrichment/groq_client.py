"""GroQ LLM client with retry, rate-limit handling, and JSON response parsing."""

from __future__ import annotations

import json
import re
import time
from typing import Any, Optional

from src.utils.logger import get_logger
from src.utils.metrics import PipelineMetrics
from src.utils.security import SecureConfig

logger = get_logger(__name__)


class GroqClient:
    """Thin, production-hardened wrapper around the Groq SDK.

    Features:
    - Lazy client initialisation
    - Automatic retry with exponential backoff on rate limits
    - Structured JSON extraction from LLM responses
    - Prompt token estimation for cost tracking
    """

    def __init__(
        self,
        config: SecureConfig,
        metrics: PipelineMetrics | None = None,
    ) -> None:
        self.config = config
        self.metrics = metrics
        self._client: Any = None

        # Read model settings from config
        self.model = config.settings.groq_model
        self.temperature = config.settings.groq_temperature
        self.max_tokens = config.settings.groq_max_tokens

    def _get_client(self):
        if self._client is not None:
            return self._client
        try:
            from groq import Groq
        except ImportError as e:
            raise ImportError("groq not installed. Run: pip install groq") from e

        self._client = Groq(api_key=self.config.get_groq_api_key())
        return self._client

    def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        call_type: str = "generic",
        max_attempts: int = 3,
    ) -> Optional[str]:
        """Call GroQ chat completions API and return the raw text response."""
        client = self._get_client()
        last_exc: Optional[Exception] = None

        for attempt in range(1, max_attempts + 1):
            try:
                response = client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    temperature=self.temperature,
                    max_tokens=self.max_tokens,
                )
                content = response.choices[0].message.content
                if self.metrics:
                    self.metrics.record_llm_call(call_type, success=True)
                return content

            except Exception as exc:
                last_exc = exc
                error_str = str(exc).lower()
                if self.metrics:
                    self.metrics.record_llm_call(call_type, success=False)

                if "rate_limit" in error_str or "429" in error_str:
                    wait = 2**attempt
                    logger.warning("groq_rate_limited", attempt=attempt, wait_s=wait)
                    time.sleep(wait)
                elif attempt < max_attempts:
                    wait = 2**attempt
                    logger.warning("groq_error_retrying", attempt=attempt, error=str(exc), wait_s=wait)
                    time.sleep(wait)
                else:
                    logger.error("groq_call_failed", call_type=call_type, error=str(exc))
                    raise

        if last_exc:
            raise last_exc
        return None

    def complete_json(
        self,
        system_prompt: str,
        user_prompt: str,
        call_type: str = "generic",
    ) -> Optional[Any]:
        """Call GroQ and parse the response as JSON. Returns None on parse failure."""
        raw = self.complete(system_prompt, user_prompt, call_type=call_type)
        if not raw:
            return None
        return self._extract_json(raw)

    @staticmethod
    def _extract_json(text: str) -> Optional[Any]:
        """Extract the first valid JSON object/array from an LLM response."""
        # Try direct parse first
        stripped = text.strip()
        try:
            return json.loads(stripped)
        except json.JSONDecodeError:
            pass

        # Strip markdown fences
        fence_match = re.search(r"```(?:json)?\s*([\s\S]+?)```", stripped)
        if fence_match:
            try:
                return json.loads(fence_match.group(1).strip())
            except json.JSONDecodeError:
                pass

        # Find first { or [ and try to parse from there
        for start_char, end_char in [('{', '}'), ('[', ']')]:
            start = stripped.find(start_char)
            if start != -1:
                end = stripped.rfind(end_char)
                if end > start:
                    try:
                        return json.loads(stripped[start: end + 1])
                    except json.JSONDecodeError:
                        continue

        logger.warning("json_parse_failed", preview=text[:200])
        return None
