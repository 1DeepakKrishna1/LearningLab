"""Abstract base classes for all guardrails."""
from __future__ import annotations

import abc
import asyncio
import logging
import time
from typing import TYPE_CHECKING, Optional

from guardrails.models.types import (
    GuardrailConfig,
    GuardrailResult,
    GuardrailStatus,
    GuardrailType,
    PipelineContext,
)

if TYPE_CHECKING:
    from guardrails.llm.client import LLMClient

logger = logging.getLogger(__name__)


class BaseGuardrail(abc.ABC):
    """Abstract base class every guardrail must extend."""

    guardrail_type: GuardrailType  # set by InputGuardrail / OutputGuardrail

    def __init__(
        self,
        config: GuardrailConfig,
        llm_client: Optional["LLMClient"] = None,
    ) -> None:
        _validate_sequence_id(config.sequence_id)
        self.config = config
        self.llm_client = llm_client

    # ------------------------------------------------------------------
    # Public properties
    # ------------------------------------------------------------------

    @property
    def sequence_id(self) -> int:
        return self.config.sequence_id

    @property
    def name(self) -> str:
        return self.config.name

    def is_active(self, mapped_number: int) -> bool:
        """Return True when this guardrail's bit is set in *mapped_number*."""
        return bool(mapped_number & self.sequence_id)

    # ------------------------------------------------------------------
    # Abstract core
    # ------------------------------------------------------------------

    @abc.abstractmethod
    async def _execute(
        self, content: str, context: PipelineContext
    ) -> GuardrailResult:
        """Subclasses implement the actual guard logic here."""

    # ------------------------------------------------------------------
    # Public execution wrapper (timing + error handling)
    # ------------------------------------------------------------------

    async def execute(
        self, content: str, context: PipelineContext
    ) -> GuardrailResult:
        """Run *_execute* with timeout, error capture, and structured logging."""
        start = time.perf_counter()
        try:
            result = await asyncio.wait_for(
                self._execute(content, context),
                timeout=self.config.timeout_seconds,
            )
        except asyncio.TimeoutError:
            result = self._error_result(
                "TIMEOUT",
                f"Timed out after {self.config.timeout_seconds}s",
            )
        except Exception as exc:
            logger.exception(
                "Guardrail execution error",
                extra={"guardrail": self.name, "correlation_id": context.correlation_id},
            )
            result = self._error_result("ERROR", str(exc))

        result.duration_ms = (time.perf_counter() - start) * 1000
        logger.debug(
            "Guardrail executed",
            extra={
                "guardrail": self.name,
                "status": result.status,
                "score": result.score,
                "duration_ms": round(result.duration_ms, 2),
                "correlation_id": context.correlation_id,
            },
        )
        return result

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _error_result(self, flag: str, message: str) -> GuardrailResult:
        status = (
            GuardrailStatus.ERROR
            if self.config.fail_on_error
            else GuardrailStatus.SKIP
        )
        return GuardrailResult(
            guardrail_id=str(self.sequence_id),
            guardrail_name=self.name,
            status=status,
            score=0.0,
            message=message,
            flags=[flag],
        )

    def _pass_result(
        self,
        score: float = 1.0,
        message: str = "OK",
        modified_content: Optional[str] = None,
    ) -> GuardrailResult:
        return GuardrailResult(
            guardrail_id=str(self.sequence_id),
            guardrail_name=self.name,
            status=GuardrailStatus.PASS,
            score=score,
            message=message,
            modified_content=modified_content,
        )

    def _fail_result(
        self,
        score: float = 0.0,
        message: str = "Failed",
        flags: Optional[list] = None,
    ) -> GuardrailResult:
        return GuardrailResult(
            guardrail_id=str(self.sequence_id),
            guardrail_name=self.name,
            status=GuardrailStatus.FAIL,
            score=score,
            message=message,
            flags=flags or [],
        )

    def _skip_result(self, reason: str = "Skipped") -> GuardrailResult:
        return GuardrailResult(
            guardrail_id=str(self.sequence_id),
            guardrail_name=self.name,
            status=GuardrailStatus.SKIP,
            score=1.0,
            message=reason,
        )


class InputGuardrail(BaseGuardrail):
    """Base class for all pre-LLM guardrails."""

    guardrail_type = GuardrailType.INPUT


class OutputGuardrail(BaseGuardrail):
    """Base class for all post-LLM guardrails."""

    guardrail_type = GuardrailType.OUTPUT


# ---------------------------------------------------------------------------
# Internal helper
# ---------------------------------------------------------------------------

def _validate_sequence_id(sequence_id: int) -> None:
    if sequence_id <= 0 or (sequence_id & (sequence_id - 1)) != 0:
        raise ValueError(
            f"sequence_id must be a positive power of 2, got {sequence_id}"
        )
