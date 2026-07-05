"""Persist user-created workflows to myworkflow.json."""
import json
import os
from pathlib import Path

from models import Workflow, WorkflowNode, WorkflowEdge, NodePosition, WorkflowStatus
from db import workflows_db
from config import get_data_dir

_FILE = get_data_dir() / os.getenv("MYWORKFLOW", "myworkflow.json")


def save_user_workflows() -> None:
    """Write all non-template workflows to myworkflow.json."""
    user_workflows = [
        wf.model_dump(mode="json")
        for wf in workflows_db.values()
        if not wf.is_template
    ]
    _FILE.write_text(json.dumps(user_workflows, indent=2, default=str), encoding="utf-8")


def load_user_workflows() -> None:
    """Read myworkflow.json and populate workflows_db (skips if file absent)."""
    if not _FILE.exists():
        return
    try:
        records = json.loads(_FILE.read_text(encoding="utf-8-sig"))
        for wd in records:
            nodes = [
                WorkflowNode(
                    id=n["id"],
                    node_kind=n.get("node_kind", "agent"),
                    agent_id=n.get("agent_id"),
                    tool_id=n.get("tool_id"),
                    position=NodePosition(**n["position"]),
                    data=n.get("data", {}),
                )
                for n in wd.get("nodes", [])
            ]
            edges = [
                WorkflowEdge(
                    id=e["id"],
                    source=e["source"],
                    target=e["target"],
                    label=e.get("label"),
                    type=e.get("type", "smoothstep"),
                )
                for e in wd.get("edges", [])
            ]
            wf = Workflow(
                id=wd["id"],
                name=wd["name"],
                description=wd["description"],
                status=WorkflowStatus(wd["status"]),
                nodes=nodes,
                edges=edges,
                is_template=False,
                tags=wd.get("tags", []),
            )
            workflows_db[wf.id] = wf
        print(f"Loaded {len(records)} user workflow(s) from {_FILE.name}")
    except Exception as exc:
        print(f"Could not load {_FILE.name}: {exc}")
