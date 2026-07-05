"""
base.py — Unified interfaces for all 21 agentic AI patterns.

Every pattern module:
  1. Inherits from BasePattern
  2. Returns a PatternResult from its run() method
  3. Exposes PATTERN_NUMBER and PATTERN_NAME class attributes
"""
from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class PatternResult:
    """Standardized result container returned by every pattern's run() method."""

    pattern_name: str
    pattern_number: int
    success: bool
    input_data: Any
    output_data: Any
    steps: List[Dict[str, Any]] = field(default_factory=list)
    execution_time_ms: float = 0.0
    token_usage: Dict[str, int] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None

    def summary(self) -> str:
        status = "OK" if self.success else "FAILED"
        lines = [
            f"Pattern {self.pattern_number:02d}: {self.pattern_name}  [{status}]",
            f"  Time   : {self.execution_time_ms:.0f} ms",
            f"  Input  : {str(self.input_data)[:120]}",
        ]
        if self.success:
            lines.append(f"  Output : {str(self.output_data)[:300]}")
        else:
            lines.append(f"  Error  : {self.error}")
        if self.steps:
            lines.append(f"  Steps  : {len(self.steps)} recorded")
        return "\n".join(lines)


class BasePattern(ABC):
    """Abstract base class that all 21 pattern implementations must subclass."""

    PATTERN_NUMBER: int = 0
    PATTERN_NAME: str = "Unnamed Pattern"
    DESCRIPTION: str = ""

    def __init__(self, llm_client: Any) -> None:
        self.llm = llm_client

    @abstractmethod
    def build_graph(self) -> Any:
        """Construct and compile the LangGraph StateGraph for this pattern."""
        ...

    @abstractmethod
    def run(self, input_data: Any, **kwargs: Any) -> PatternResult:
        """Execute the pattern with the provided input and return a PatternResult."""
        ...

    def _timed_run(self, fn: Any, *args: Any, **kwargs: Any):
        """Helper: run fn(*args, **kwargs) and return (result, elapsed_ms)."""
        t0 = time.perf_counter()
        result = fn(*args, **kwargs)
        elapsed_ms = (time.perf_counter() - t0) * 1000
        return result, elapsed_ms

    def _make_result(
        self,
        *,
        success: bool,
        input_data: Any,
        output_data: Any,
        elapsed_ms: float = 0.0,
        steps: Optional[List[Dict[str, Any]]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
    ) -> PatternResult:
        return PatternResult(
            pattern_name=self.PATTERN_NAME,
            pattern_number=self.PATTERN_NUMBER,
            success=success,
            input_data=input_data,
            output_data=output_data,
            steps=steps or [],
            execution_time_ms=elapsed_ms,
            metadata=metadata or {},
            error=error,
        )
