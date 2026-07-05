"""Workflow Execution Engine.

Supports two execution modes controlled by the ``EXECUTION_MODE`` env-var:

* ``topological`` (default) – pure Python topological sort (Kahn's algorithm).
* ``langgraph``              – LangGraph ``StateGraph`` compilation and invoke.

Usage::

    from core.engine import WorkflowEngine

    engine = WorkflowEngine()
    result = engine.execute("Customer Onboarding (Myflow)", {"customer_id": "C001"})
"""

from __future__ import annotations

import json
import os
from collections import deque
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from dotenv import load_dotenv

from core import state as state_utils
from core.registry import Registry, load_all

load_dotenv()


# ---------------------------------------------------------------------------
# Workflow loader
# ---------------------------------------------------------------------------

def _load_workflows(path: str) -> List[Dict[str, Any]]:
    with open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    return data if isinstance(data, list) else [data]


def _find_workflow(
    workflows: List[Dict[str, Any]], name_or_id: str
) -> Optional[Dict[str, Any]]:
    for wf in workflows:
        if wf.get("name") == name_or_id or wf.get("id") == name_or_id:
            return wf
    return None


# ---------------------------------------------------------------------------
# Graph helpers
# ---------------------------------------------------------------------------

def _topological_order(
    nodes: List[Dict[str, Any]], edges: List[Dict[str, Any]]
) -> List[str]:
    """Kahn's algorithm – returns node IDs in execution order."""
    node_ids = [n["id"] for n in nodes]
    adj: Dict[str, List[str]] = {nid: [] for nid in node_ids}
    in_degree: Dict[str, int] = {nid: 0 for nid in node_ids}

    for edge in edges:
        src, tgt = edge["source"], edge["target"]
        if src in adj:
            adj[src].append(tgt)
        if tgt in in_degree:
            in_degree[tgt] += 1

    queue: deque[str] = deque(
        nid for nid, deg in in_degree.items() if deg == 0
    )
    order: List[str] = []

    while queue:
        nid = queue.popleft()
        order.append(nid)
        for neighbor in adj.get(nid, []):
            in_degree[neighbor] -= 1
            if in_degree[neighbor] == 0:
                queue.append(neighbor)

    return order


def _entry_and_exit(
    nodes: List[Dict[str, Any]], edges: List[Dict[str, Any]]
) -> Tuple[List[str], List[str]]:
    target_ids = {e["target"] for e in edges}
    source_ids = {e["source"] for e in edges}
    entries = [n["id"] for n in nodes if n["id"] not in target_ids]
    exits = [n["id"] for n in nodes if n["id"] not in source_ids]
    return entries, exits


# ---------------------------------------------------------------------------
# Execution backends
# ---------------------------------------------------------------------------

def _execute_node(
    node: Dict[str, Any],
    state: Dict[str, Any],
) -> Dict[str, Any]:
    """Execute a single workflow node and update state in-place."""
    node_id = node["id"]
    node_data = node.get("data") or {}
    agent_id = node.get("agent_id") or ""
    node_name = node_data.get("name", node_id)

    agent = Registry.get_agent(agent_id)
    if agent is None:
        state_utils.log_event(
            state, "WARNING", node_id, node_name, "skipped",
            {"reason": f"No agent registered for '{agent_id}'"},
        )
        return state

    # Merge node-level tool configs into node_data so agents can read them
    node_config = dict(node_data)
    node_config.setdefault("tools", [])
    node_config.setdefault("toolConfigs", {})

    state["current_node_id"] = node_id
    state["current_node_config"] = node_config

    state_utils.begin_node_record(state, node_id, node_name, agent_id)
    state_utils.log_event(state, "INFO", node_id, node_name, "started",
                          {"agent_id": agent_id})

    try:
        state = agent.run(state)
        state_utils.complete_node_record(
            state, node_id, dict(state.get("current_data", {}))
        )
        state_utils.log_event(state, "INFO", node_id, node_name, "completed")
    except Exception as exc:  # pylint: disable=broad-except
        err = str(exc)
        state_utils.complete_node_record(state, node_id, {}, error=err)
        state_utils.log_event(
            state, "ERROR", node_id, node_name, "failed", {"error": err}
        )
        state["status"] = "failed"
        state["error"] = err

    return state


def _run_topological(
    workflow: Dict[str, Any], state: Dict[str, Any]
) -> Dict[str, Any]:
    nodes = workflow.get("nodes", [])
    edges = workflow.get("edges", [])
    node_map = {n["id"]: n for n in nodes}
    order = _topological_order(nodes, edges)

    for nid in order:
        if state.get("status") == "failed":
            break
        node = node_map.get(nid)
        if node is None:
            continue
        state = _execute_node(node, state)

    return state


def _run_langgraph(
    workflow: Dict[str, Any], state: Dict[str, Any]
) -> Dict[str, Any]:
    try:
        from langgraph.graph import END, StateGraph  # type: ignore
    except ImportError:
        raise RuntimeError(
            "langgraph is not installed.  "
            "Run `pip install langgraph` or set EXECUTION_MODE=topological."
        )

    nodes = workflow.get("nodes", [])
    edges = workflow.get("edges", [])
    node_map = {n["id"]: n for n in nodes}

    def _safe(nid: str) -> str:
        """LangGraph node names must be valid Python identifiers."""
        return nid.replace("-", "_")

    graph: StateGraph = StateGraph(dict)

    # Add one LangGraph node per workflow node
    for node in nodes:
        nid = node["id"]
        _node = node  # capture for closure

        def _make_fn(captured_node: Dict[str, Any]):
            def _fn(s: Dict[str, Any]) -> Dict[str, Any]:
                return _execute_node(captured_node, dict(s))
            return _fn

        graph.add_node(_safe(nid), _make_fn(_node))

    # Add edges
    for edge in edges:
        graph.add_edge(_safe(edge["source"]), _safe(edge["target"]))

    # Wire exit nodes → END
    _, exit_ids = _entry_and_exit(nodes, edges)
    for eid in exit_ids:
        graph.add_edge(_safe(eid), END)

    # Set entry point
    entry_ids, _ = _entry_and_exit(nodes, edges)
    if not entry_ids:
        raise RuntimeError("Workflow has no entry node (cycle detected).")
    graph.set_entry_point(_safe(entry_ids[0]))

    app = graph.compile()
    result = app.invoke(state)
    return result


# ---------------------------------------------------------------------------
# Public engine
# ---------------------------------------------------------------------------

class WorkflowEngine:
    """High-level facade for loading and executing workflows."""

    def __init__(
        self,
        workflow_file: Optional[str] = None,
        execution_mode: Optional[str] = None,
    ) -> None:
        load_all()  # ensure agents + tools are registered

        wf_path = workflow_file or os.getenv("WORKFLOW_FILE", "myworkflow.json")
        self._workflows = _load_workflows(
            str(Path(__file__).parent.parent / wf_path)
            if not os.path.isabs(wf_path)
            else wf_path
        )
        self._mode = (
            execution_mode
            or os.getenv("EXECUTION_MODE", "topological")
        ).lower()

    # ------------------------------------------------------------------

    def list_workflows(self) -> List[Dict[str, Any]]:
        return [
            {
                "id": wf.get("id"),
                "name": wf.get("name"),
                "description": wf.get("description"),
                "status": wf.get("status"),
                "tags": wf.get("tags", []),
                "node_count": len(wf.get("nodes", [])),
                "edge_count": len(wf.get("edges", [])),
            }
            for wf in self._workflows
        ]

    def get_workflow(self, name_or_id: str) -> Optional[Dict[str, Any]]:
        return _find_workflow(self._workflows, name_or_id)

    def execute(
        self,
        workflow_name_or_id: str,
        start_properties: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Execute a workflow and return the full execution state."""
        workflow = _find_workflow(self._workflows, workflow_name_or_id)
        if workflow is None:
            raise ValueError(f"Workflow '{workflow_name_or_id}' not found.")

        state = state_utils.new_execution_state(
            workflow_id=workflow["id"],
            workflow_name=workflow["name"],
            start_properties=start_properties,
        )

        state_utils.log_event(
            state, "INFO", "", workflow["name"], "workflow_started",
            {"mode": self._mode, "nodes": len(workflow.get("nodes", []))},
        )

        try:
            if self._mode == "langgraph":
                state = _run_langgraph(workflow, state)
            else:
                state = _run_topological(workflow, state)
        except Exception as exc:  # pylint: disable=broad-except
            state["status"] = "failed"
            state["error"] = str(exc)
            state_utils.log_event(
                state, "ERROR", "", workflow["name"], "workflow_failed",
                {"error": str(exc)},
            )
            return state

        if state.get("status") != "failed":
            state["status"] = "completed"

        import datetime as _dt
        state["completed_at"] = _dt.datetime.now(_dt.timezone.utc).isoformat()

        # Capture end_properties from last node's output
        nodes = workflow.get("nodes", [])
        edges = workflow.get("edges", [])
        _, exit_ids = _entry_and_exit(nodes, edges)
        if exit_ids:
            last_record = state["node_records"].get(exit_ids[-1], {})
            state["end_properties"] = last_record.get("output", {})

        state_utils.log_event(
            state, "INFO", "", workflow["name"], "workflow_completed",
            {"status": state["status"]},
        )
        return state
