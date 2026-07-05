import uuid
from datetime import datetime
from typing import List, Dict, Any
from fastapi import APIRouter, HTTPException, Body
from pydantic import BaseModel

from models import Tool, ToolCreate, ToolType
from db import tools_db

router = APIRouter()


@router.get("", response_model=List[Tool])
async def list_tools():
    return list(tools_db.values())


@router.get("/{tool_id}", response_model=Tool)
async def get_tool(tool_id: str):
    if tool_id not in tools_db:
        raise HTTPException(status_code=404, detail="Tool not found")
    return tools_db[tool_id]


@router.post("", response_model=Tool)
async def create_tool(body: ToolCreate):
    tool = Tool(id=str(uuid.uuid4()), **body.model_dump(), review_status="pending")
    tools_db[tool.id] = tool
    _save_library()
    return tool


@router.put("/{tool_id}", response_model=Tool)
async def update_tool(tool_id: str, body: ToolCreate):
    if tool_id not in tools_db:
        raise HTTPException(status_code=404, detail="Tool not found")
    updated = tools_db[tool_id].model_copy(update=body.model_dump(exclude_unset=True))
    tools_db[tool_id] = updated
    _save_library()
    return updated


@router.delete("/{tool_id}")
async def delete_tool(tool_id: str):
    if tool_id not in tools_db:
        raise HTTPException(status_code=404, detail="Tool not found")
    del tools_db[tool_id]
    _save_library()
    return {"deleted": tool_id}


def _save_library():
    from library_persistence import save_library_data
    save_library_data()


# ── Export ─────────────────────────────────────────────────────────────────

@router.get("/{tool_id}/export")
async def export_tool(tool_id: str):
    if tool_id not in tools_db:
        raise HTTPException(status_code=404, detail="Tool not found")
    return {
        "exportId": str(uuid.uuid4()),
        "exportedAt": datetime.utcnow().isoformat(),
        "exportVersion": "1.0",
        "kind": "tool",
        "tools": [tools_db[tool_id].model_dump(mode="json")],
    }


# ── Import preview ─────────────────────────────────────────────────────────

@router.post("/import/preview")
async def preview_tool_import(payload: dict = Body(...)):
    if "tools" not in payload or not isinstance(payload["tools"], list):
        raise HTTPException(status_code=400, detail="Invalid export file: missing 'tools'")
    return {
        "exportId": payload.get("exportId"),
        "tools": [
            {**t, "_status": "exists" if t.get("id") in tools_db else "new"}
            for t in payload["tools"]
        ],
    }


# ── Import apply ───────────────────────────────────────────────────────────

class ToolImportApply(BaseModel):
    export_data: Dict[str, Any]
    decisions: Dict[str, str]  # tool_id -> "add"|"update"|"skip"


@router.post("/import/apply")
async def apply_tool_import(payload: ToolImportApply):
    data = payload.export_data
    decisions = payload.decisions or {}
    results: Dict[str, list] = {"added": [], "updated": [], "skipped": [], "errors": []}

    def _rec(bucket: str, eid: str, ename: str):
        results[bucket].append({"type": "tool", "id": eid, "name": ename})

    changed = False
    for td in data.get("tools", []):
        action = decisions.get(td["id"], "skip")
        if action == "skip":
            _rec("skipped", td["id"], td.get("name", "")); continue
        existing = td["id"] in tools_db
        if action == "add" and existing:
            _rec("skipped", td["id"], td.get("name", "")); continue
        try:
            tool = Tool(
                id=td["id"], name=td["name"], description=td["description"],
                type=ToolType(td["type"]), properties=td.get("properties", {}),
                icon=td.get("icon", "wrench"),
                review_status=td.get("review_status", "approved"),
            )
            tools_db[tool.id] = tool
            changed = True
            _rec("updated" if existing else "added", tool.id, tool.name)
        except Exception as exc:
            results["errors"].append({"type": "tool", "id": td.get("id", ""), "name": td.get("name", ""), "error": str(exc)})

    if changed:
        _save_library()
    return results
