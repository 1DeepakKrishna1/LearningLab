"""Base class for all workflow tools."""

from abc import ABC, abstractmethod
from typing import Any, Dict


class BaseTool(ABC):
    """Abstract base for every tool in the execution engine.

    Subclasses must implement :py:meth:`tool_id`, :py:meth:`name`,
    :py:meth:`description`, and :py:meth:`run`.
    """

    @property
    @abstractmethod
    def tool_id(self) -> str:
        """Unique tool identifier matching ``dummy_data.json`` (e.g. ``tool-001``)."""

    @abstractmethod
    def name(self) -> str:
        """Human-readable tool name."""

    @abstractmethod
    def description(self) -> str:
        """Short description of what this tool does."""

    @abstractmethod
    def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the tool.

        Parameters
        ----------
        input_data:
            Merged dict of ``current_data`` + any per-tool overrides from the
            node's ``toolConfigs`` block.

        Returns
        -------
        Dict[str, Any]
            Tool result.  Keys should be descriptive and will be merged into
            the node's ``tool_executions`` record.
        """
