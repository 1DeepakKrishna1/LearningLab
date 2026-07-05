"""Base class for all workflow agents."""

from abc import ABC, abstractmethod
from typing import Any, Dict


class BaseAgent(ABC):
    """Abstract base for every agent in the execution engine.

    Subclasses must implement :py:meth:`agent_id`, :py:meth:`name`,
    :py:meth:`description`, and :py:meth:`run`.
    """

    @property
    @abstractmethod
    def agent_id(self) -> str:
        """Unique agent identifier matching ``dummy_data.json`` (e.g. ``agent-001``)."""

    @abstractmethod
    def name(self) -> str:
        """Human-readable agent name."""

    @abstractmethod
    def description(self) -> str:
        """Short description of what this agent does."""

    @abstractmethod
    def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the agent.

        Parameters
        ----------
        state:
            Workflow execution state dict.  Key fields available to every agent:

            * ``current_data``       – dict flowing between nodes (read & write)
            * ``current_node_id``    – id of the node being executed
            * ``current_node_config``– node ``data`` block from the workflow JSON
            * ``start_properties``   – original API-call input
            * ``execution_log``      – list of log-entry dicts (append via
              :py:func:`core.state.log_event`)
            * ``node_records``       – per-node execution records

        Returns
        -------
        Dict[str, Any]
            The (possibly mutated) state dict.  At minimum the agent should
            merge its output into ``state["current_data"]``.
        """
