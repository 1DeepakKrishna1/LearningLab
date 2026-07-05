"""Persist library changes (tools, agents, templates) back to dummy_data.json."""
import json
import os
from pathlib import Path

from config import get_data_dir

_DATA_FILE = get_data_dir() / os.getenv("MOCKDATA", "dummy_data.json")


def save_library_data():
    """Write current tools, agents, and template workflows to dummy_data.json."""
    from db import tools_db, agents_db, workflows_db, library_workflow_ids

    data = {
        "tools": [t.model_dump(mode="json") for t in tools_db.values()],
        "agents": [a.model_dump(mode="json") for a in agents_db.values()],
        "templates": [
            w.model_dump(mode="json")
            for w in workflows_db.values()
            if w.id in library_workflow_ids
        ],
    }
    _DATA_FILE.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
