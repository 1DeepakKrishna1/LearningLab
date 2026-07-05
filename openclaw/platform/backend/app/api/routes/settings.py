"""Platform settings routes (stored in data/settings.json)."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends

from ..deps import ContainerDep, require

router = APIRouter(tags=["settings"])

_DEFAULTS: dict[str, Any] = {
    "default_llm_provider": "anthropic",
    "default_llm_model": "claude-sonnet-4-6",
    "messaging_provider": "console",
    "max_parallel_nodes": 8,
    "theme": "light",
}


def _path(container: ContainerDep) -> Path:
    return Path(container.settings.data_dir) / "settings.json"


@router.get("/settings", dependencies=[Depends(require("settings:read"))])
async def get_settings(container: ContainerDep) -> dict:
    p = _path(container)
    runtime = {
        "default_llm_provider": container.settings.default_llm_provider,
        "default_llm_model": container.settings.default_llm_model,
        "messaging_provider": container.settings.messaging_provider,
        "max_parallel_nodes": container.settings.max_parallel_nodes,
    }
    stored = json.loads(p.read_text("utf-8")) if p.exists() else {}
    return {**_DEFAULTS, **runtime, **stored}


@router.put("/settings", dependencies=[Depends(require("settings:write"))])
async def update_settings(body: dict, container: ContainerDep) -> dict:
    p = _path(container)
    current = json.loads(p.read_text("utf-8")) if p.exists() else {}
    current.update(body)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(current, indent=2, ensure_ascii=False), "utf-8")
    return current
