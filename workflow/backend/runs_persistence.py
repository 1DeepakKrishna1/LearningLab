"""Load mock execution runs from mockRunData.json into executions_db on startup."""
import json
import os
from datetime import datetime

from models import ExecutionRun, StepResult, ExecutionStatus
from db import executions_db
from config import get_data_dir

_FILE = get_data_dir() / os.getenv("MOCKRUNDATA", "mockRunData.json")


def _parse_dt(value) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    # Strip sub-second fractions beyond 6 digits and trailing Z
    s = str(value).rstrip("Z")
    for fmt in ("%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    return None


def load_mock_runs() -> None:
    """Read mockRunData.json and populate executions_db (skips if file absent)."""
    if not _FILE.exists():
        print(f"Mock runs file not found: {_FILE.name} — skipping.")
        return
    try:
        records = json.loads(_FILE.read_text(encoding="utf-8-sig"))
        count = 0
        for rd in records:
            steps = [
                StepResult(
                    node_id=s["node_id"],
                    agent_name=s["agent_name"],
                    node_kind=s.get("node_kind", "agent"),
                    status=ExecutionStatus(s["status"]),
                    started_at=_parse_dt(s["started_at"]),
                    completed_at=_parse_dt(s.get("completed_at")),
                    input=s.get("input", {}),
                    output=s.get("output", {}),
                    logs=s.get("logs", []),
                    duration_ms=s.get("duration_ms"),
                    requires_human_input=s.get("requires_human_input", False),
                    judgment_options=s.get("judgment_options", []),
                    input_fields=s.get("input_fields", {}),
                    human_response=s.get("human_response"),
                )
                for s in rd.get("steps", [])
            ]
            run = ExecutionRun(
                id=rd["id"],
                workflow_id=rd["workflow_id"],
                status=ExecutionStatus(rd["status"]),
                steps=steps,
                started_at=_parse_dt(rd["started_at"]),
                completed_at=_parse_dt(rd.get("completed_at")),
                total_duration_ms=rd.get("total_duration_ms"),
            )
            executions_db[run.id] = run
            count += 1
        print(f"Loaded {count} mock execution run(s) from {_FILE.name}")
    except Exception as exc:
        print(f"Could not load {_FILE.name}: {exc}")
