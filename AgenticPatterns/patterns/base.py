"""Base class shared by all agentic pattern implementations."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from llm_client import GroqClient

_SEPARATOR = "─" * 60


class BasePattern(ABC):
    """
    Abstract base for every agentic pattern.

    Subclasses receive a shared ``GroqClient`` instance and must
    implement ``run()``.
    """

    #: Human-readable name shown in demo output.
    name: str = "Pattern"

    def __init__(self, client: GroqClient) -> None:
        self.client = client

    @abstractmethod
    async def run(self, *args: Any, **kwargs: Any) -> Any:
        """Execute the pattern and return the result."""

    # ------------------------------------------------------------------
    # Display helpers
    # ------------------------------------------------------------------

    def print_header(self) -> None:
        print(f"\n{'═' * 60}")
        print(f"  Pattern: {self.name}")
        print(f"{'═' * 60}")

    def print_step(self, label: str, content: str) -> None:
        print(f"\n{_SEPARATOR}")
        print(f"  {label}")
        print(_SEPARATOR)
        print(content.strip())

    def print_result(self, content: str) -> None:
        print(f"\n>>> Final Result <<<")
        print(content.strip())
