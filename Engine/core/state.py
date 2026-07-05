"""Workflow execution state helpers."""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# State factory
# ---------------------------------------------------------------------------

def new_execution_state(
    workflow_id: str,
    workflow_name: str,
    start_properties: Dict[str, Any],
) -> Dict[str, Any]:
    """Create a fresh execution-state dict for one workflow run."""
    return {
        "execution_id": str(uuid.uuid4()),
        "workflow_id": workflow_id,
        "workflow_name": workflow_name,
        "status": "running",
        "error": None,
        # Input supplied by the caller
        "start_properties": start_properties,
        # Populated by the End node (last node's output)
        "end_properties": {},
        # Engine sets these before calling agent.run()
        "current_node_id": "",
        "current_node_config": {},
        # Flowing data between nodes; seeded with start_properties
        "current_data": dict(start_properties),
        # Execution history
        "node_records": {},   # {node_id: record_dict}
        "execution_log": [],  # [log_entry_dict, ...]
        "started_at": _now(),
        "completed_at": None,
    }


# ---------------------------------------------------------------------------
# Logging helpers
# ---------------------------------------------------------------------------

def log_event(
    state: Dict[str, Any],
    level: str,
    node_id: str,
    node_name: str,
    event: str,
    details: Optional[Dict[str, Any]] = None,
) -> None:
    """Append a structured log entry to ``state["execution_log"]``."""
    state["execution_log"].append(
        {
            "timestamp": _now(),
            "level": level,
            "node_id": node_id,
            "node_name": node_name,
            "event": event,
            "details": details or {},
        }
    )


# ---------------------------------------------------------------------------
# Node-record helpers
# ---------------------------------------------------------------------------

def begin_node_record(
    state: Dict[str, Any],
    node_id: str,
    node_name: str,
    agent_id: str,
) -> None:
    """Initialise a node execution record at the start of agent execution."""
    state["node_records"][node_id] = {
        "node_id": node_id,
        "node_name": node_name,
        "agent_id": agent_id,
        "status": "running",
        "started_at": _now(),
        "completed_at": None,
        "input": dict(state.get("current_data", {})),
        "output": {},
        "tool_executions": [],
        "error": None,
    }


def complete_node_record(
    state: Dict[str, Any],
    node_id: str,
    output: Dict[str, Any],
    error: Optional[str] = None,
) -> None:
    """Finalise a node execution record after agent execution completes."""
    record = state["node_records"].get(node_id)
    if record is None:
        return
    record["status"] = "failed" if error else "completed"
    record["completed_at"] = _now()
    record["output"] = output
    record["error"] = error


def add_tool_execution(
    state: Dict[str, Any],
    node_id: str,
    tool_id: str,
    tool_name: str,
    tool_input: Dict[str, Any],
    tool_output: Dict[str, Any],
) -> None:
    """Record a tool execution inside the parent node's record."""
    record = state["node_records"].get(node_id)
    if record is None:
        return
    record["tool_executions"].append(
        {
            "tool_id": tool_id,
            "tool_name": tool_name,
            "executed_at": _now(),
            "input": tool_input,
            "output": tool_output,
        }
    )


# ---------------------------------------------------------------------------
# Convenience accessors
# ---------------------------------------------------------------------------

def get_execution_summary(state: Dict[str, Any]) -> Dict[str, Any]:
    """Return a lightweight summary of the execution state."""
    return {
        "execution_id": state["execution_id"],
        "workflow_id": state["workflow_id"],
        "workflow_name": state["workflow_name"],
        "status": state["status"],
        "started_at": state["started_at"],
        "completed_at": state["completed_at"],
        "nodes_executed": len(state["node_records"]),
        "log_entries": len(state["execution_log"]),
        "error": state.get("error"),
    }
