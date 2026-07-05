"""Core data models for the guardrails framework."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional


class GuardrailStatus(str, Enum):
    PASS = "pass"
    FAIL = "fail"
    SKIP = "skip"
    ERROR = "error"


class GuardrailType(str, Enum):
    INPUT = "input"
    OUTPUT = "output"


@dataclass
class GuardrailResult:
    guardrail_id: str
    guardrail_name: str
    status: GuardrailStatus
    score: float  # 0.0–1.0; higher = safer / better quality
    message: str
    flags: List[str] = field(default_factory=list)
    modified_content: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    duration_ms: float = 0.0

    @property
    def passed(self) -> bool:
        return self.status == GuardrailStatus.PASS

    @property
    def failed(self) -> bool:
        return self.status == GuardrailStatus.FAIL


@dataclass
class PipelineContext:
    correlation_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    original_input: str = ""
    sanitized_input: Optional[str] = None
    llm_response: Optional[str] = None
    final_output: Optional[str] = None
    input_results: List[GuardrailResult] = field(default_factory=list)
    output_results: List[GuardrailResult] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def effective_input(self) -> str:
        """The current working input (original or sanitized if modified by a guardrail)."""
        return self.sanitized_input if self.sanitized_input is not None else self.original_input

    @property
    def input_passed(self) -> bool:
        return all(
            r.status in (GuardrailStatus.PASS, GuardrailStatus.SKIP)
            for r in self.input_results
        )

    @property
    def output_passed(self) -> bool:
        return all(
            r.status in (GuardrailStatus.PASS, GuardrailStatus.SKIP)
            for r in self.output_results
        )


@dataclass
class GuardrailConfig:
    name: str
    sequence_id: int  # Must be a power of 2
    enabled: bool = True
    threshold: float = 0.5
    fail_on_error: bool = False
    timeout_seconds: float = 5.0
    parameters: Dict[str, Any] = field(default_factory=dict)
