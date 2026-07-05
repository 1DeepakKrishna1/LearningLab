"""Groq API LLM client with retry logic and timeout handling."""
from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, List, Optional

import httpx

from guardrails.llm.client import LLMClient, LLMMessage, LLMResponse
from guardrails.utils.exceptions import LLMClientError, LLMRateLimitError

logger = logging.getLogger(__name__)

_GROQ_BASE_URL = "https://api.groq.com"
_CHAT_PATH = "/openai/v1/chat/completions"
_MODELS_PATH = "/openai/v1/models"
_DEFAULT_MODEL = "llama3-8b-8192"


class GroqLLMClient(LLMClient):
    """Async Groq client with exponential-backoff retry and structured prompting."""

    def __init__(
        self,
        api_key: str,
        model: str = _DEFAULT_MODEL,
        max_retries: int = 3,
        base_timeout: float = 10.0,
    ) -> None:
        self._model = model
        self._max_retries = max_retries
        self._base_timeout = base_timeout
        self._http = httpx.AsyncClient(
            base_url=_GROQ_BASE_URL,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            timeout=base_timeout,
        )

    async def complete(
        self,
        messages: List[LLMMessage],
        *,
        temperature: float = 0.0,
        max_tokens: int = 512,
        timeout: float = 10.0,
    ) -> LLMResponse:
        payload: Dict[str, Any] = {
            "model": self._model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        last_exc: Optional[Exception] = None

        for attempt in range(1, self._max_retries + 1):
            try:
                resp = await asyncio.wait_for(
                    self._http.post(_CHAT_PATH, json=payload),
                    timeout=timeout,
                )
                if resp.status_code == 429:
                    retry_after = float(resp.headers.get("Retry-After", 1.0))
                    raise LLMRateLimitError(retry_after=retry_after)
                if resp.status_code >= 400:
                    raise LLMClientError(
                        f"Groq API error {resp.status_code}: {resp.text}",
                        retryable=resp.status_code >= 500,
                    )
                data = resp.json()
                return LLMResponse(
                    content=data["choices"][0]["message"]["content"],
                    model=data.get("model", self._model),
                    usage=data.get("usage", {}),
                )

            except LLMRateLimitError as exc:
                logger.warning(
                    "Groq rate-limited",
                    extra={"attempt": attempt, "retry_after": exc.retry_after},
                )
                last_exc = exc
                if attempt < self._max_retries:
                    await asyncio.sleep(exc.retry_after or 2**attempt)

            except LLMClientError as exc:
                if not exc.retryable or attempt >= self._max_retries:
                    raise
                backoff = 2**attempt
                logger.warning(
                    "Retryable LLM error",
                    extra={"attempt": attempt, "backoff": backoff, "error": str(exc)},
                )
                last_exc = exc
                await asyncio.sleep(backoff)

            except asyncio.TimeoutError:
                logger.warning(
                    "Groq request timed out", extra={"attempt": attempt, "timeout": timeout}
                )
                last_exc = LLMClientError("Request timed out", retryable=True)
                if attempt < self._max_retries:
                    await asyncio.sleep(2**attempt)

            except Exception as exc:
                raise LLMClientError(f"Unexpected error: {exc}") from exc

        raise last_exc or LLMClientError("All retries exhausted")

    async def health_check(self) -> bool:
        try:
            resp = await self._http.get(_MODELS_PATH, timeout=5.0)
            return resp.status_code == 200
        except Exception:
            return False

    async def aclose(self) -> None:
        await self._http.aclose()

    async def __aenter__(self) -> "GroqLLMClient":
        return self

    async def __aexit__(self, *_: Any) -> None:
        await self.aclose()
