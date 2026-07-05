"""Custom exception hierarchy for the guardrails framework."""
from __future__ import annotations

from typing import List, Optional


class GuardrailError(Exception):
    """Base exception for all guardrail errors."""

    def __init__(self, message: str, code: str = "GUARDRAIL_ERROR") -> None:
        super().__init__(message)
        self.code = code


class GuardrailExecutionError(GuardrailError):
    """Raised when a guardrail fails to execute."""

    def __init__(self, guardrail_name: str, reason: str) -> None:
        super().__init__(
            f"Guardrail '{guardrail_name}' execution failed: {reason}",
            code="GUARDRAIL_EXECUTION_ERROR",
        )
        self.guardrail_name = guardrail_name
        self.reason = reason


class GuardrailConfigError(GuardrailError):
    """Raised for invalid guardrail configuration."""

    def __init__(self, message: str) -> None:
        super().__init__(message, code="GUARDRAIL_CONFIG_ERROR")


class PipelineBlockedError(GuardrailError):
    """Raised when the pipeline is blocked by one or more failing guardrails."""

    def __init__(self, failed_guardrails: List[str]) -> None:
        names = ", ".join(failed_guardrails)
        super().__init__(
            f"Pipeline blocked by guardrails: {names}",
            code="PIPELINE_BLOCKED",
        )
        self.failed_guardrails = failed_guardrails


class LLMClientError(GuardrailError):
    """Raised when the LLM client encounters an error."""

    def __init__(self, message: str, retryable: bool = False) -> None:
        super().__init__(message, code="LLM_CLIENT_ERROR")
        self.retryable = retryable


class LLMRateLimitError(LLMClientError):
    """Raised when the LLM API rate limit is exceeded."""

    def __init__(self, retry_after: Optional[float] = None) -> None:
        super().__init__("LLM API rate limit exceeded", retryable=True)
        self.retry_after = retry_after


class RegistryError(GuardrailError):
    """Raised for registry-related errors."""

    def __init__(self, message: str) -> None:
        super().__init__(message, code="REGISTRY_ERROR")
