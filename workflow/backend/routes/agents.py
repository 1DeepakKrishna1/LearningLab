import uuid
from datetime import datetime
from typing import List, Dict, Any
from fastapi import APIRouter, HTTPException, Body
from pydantic import BaseModel

from models import Agent, AgentCreate, AgentType, Tool, ToolType
from db import agents_db, tools_db

router = APIRouter()


# ── Request bodies for tool endpoints ─────────────────────
class ToolListBody(BaseModel):
    tool_ids: List[str]


class ToolConfigBody(BaseModel):
    config: Dict[str, Any]


# ── Agent CRUD ─────────────────────────────────────────────
@router.get("", response_model=List[Agent])
async def list_agents():
    return list(agents_db.values())


@router.get("/{agent_id}", response_model=Agent)
async def get_agent(agent_id: str):
    if agent_id not in agents_db:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agents_db[agent_id]


@router.post("", response_model=Agent)
async def create_agent(body: AgentCreate):
    agent = Agent(id=str(uuid.uuid4()), review_status="pending", **body.model_dump())
    agents_db[agent.id] = agent
    _save_library()
    return agent


@router.put("/{agent_id}", response_model=Agent)
async def update_agent(agent_id: str, body: AgentCreate):
    if agent_id not in agents_db:
        raise HTTPException(status_code=404, detail="Agent not found")
    updated = agents_db[agent_id].model_copy(update=body.model_dump(exclude_unset=True))
    agents_db[agent_id] = updated
    _save_library()
    return updated


@router.delete("/{agent_id}")
async def delete_agent(agent_id: str):
    if agent_id not in agents_db:
        raise HTTPException(status_code=404, detail="Agent not found")
    del agents_db[agent_id]
    _save_library()
    return {"deleted": agent_id}


def _save_library():
    from library_persistence import save_library_data
    save_library_data()


# ── Agent tool management ──────────────────────────────────
@router.get("/{agent_id}/tools", response_model=List[Tool])
async def get_agent_tools(agent_id: str):
    """Return full Tool objects for all tools assigned to an agent."""
    if agent_id not in agents_db:
        raise HTTPException(status_code=404, detail="Agent not found")
    agent = agents_db[agent_id]
    return [tools_db[tid] for tid in agent.tools if tid in tools_db]


@router.put("/{agent_id}/tools", response_model=Agent)
async def set_agent_tools(agent_id: str, body: ToolListBody):
    """Replace the entire tool list for an agent."""
    if agent_id not in agents_db:
        raise HTTPException(status_code=404, detail="Agent not found")
    missing = [tid for tid in body.tool_ids if tid not in tools_db]
    if missing:
        raise HTTPException(status_code=404, detail=f"Tools not found: {missing}")
    # Drop configs for tools no longer assigned
    agent = agents_db[agent_id]
    pruned_configs = {tid: cfg for tid, cfg in agent.tool_configs.items() if tid in body.tool_ids}
    updated = agent.model_copy(update={"tools": body.tool_ids, "tool_configs": pruned_configs})
    agents_db[agent_id] = updated
    print(agents_db[agent_id])
    return updated


@router.post("/{agent_id}/tools/{tool_id}", response_model=Agent)
async def add_agent_tool(agent_id: str, tool_id: str):
    """Add a single tool to an agent (idempotent)."""
    if agent_id not in agents_db:
        raise HTTPException(status_code=404, detail="Agent not found")
    if tool_id not in tools_db:
        raise HTTPException(status_code=404, detail="Tool not found")
    agent = agents_db[agent_id]
    if tool_id not in agent.tools:
        updated = agent.model_copy(update={"tools": [*agent.tools, tool_id]})
        agents_db[agent_id] = updated
    return agents_db[agent_id]


@router.delete("/{agent_id}/tools/{tool_id}", response_model=Agent)
async def remove_agent_tool(agent_id: str, tool_id: str):
    """Remove a single tool from an agent and clear its config."""
    if agent_id not in agents_db:
        raise HTTPException(status_code=404, detail="Agent not found")
    agent = agents_db[agent_id]
    new_tools = [t for t in agent.tools if t != tool_id]
    new_configs = {tid: cfg for tid, cfg in agent.tool_configs.items() if tid != tool_id}
    updated = agent.model_copy(update={"tools": new_tools, "tool_configs": new_configs})
    agents_db[agent_id] = updated
    return updated


@router.put("/{agent_id}/tools/{tool_id}/config", response_model=Agent)
async def set_agent_tool_config(agent_id: str, tool_id: str, body: ToolConfigBody):
    """Set per-agent configuration overrides for a specific tool."""
    if agent_id not in agents_db:
        raise HTTPException(status_code=404, detail="Agent not found")
    if tool_id not in tools_db:
        raise HTTPException(status_code=404, detail="Tool not found")
    agent = agents_db[agent_id]
    if tool_id not in agent.tools:
        raise HTTPException(status_code=400, detail="Tool is not assigned to this agent")
    new_configs = {**agent.tool_configs, tool_id: body.config}
    updated = agent.model_copy(update={"tool_configs": new_configs})
    agents_db[agent_id] = updated
    return updated


# ── Export ─────────────────────────────────────────────────────────────────

@router.get("/{agent_id}/export")
async def export_agent(agent_id: str):
    if agent_id not in agents_db:
        raise HTTPException(status_code=404, detail="Agent not found")
    agent = agents_db[agent_id]
    referenced_tools = [
        tools_db[tid].model_dump(mode="json")
        for tid in agent.tools if tid in tools_db
    ]
    return {
        "exportId": str(uuid.uuid4()),
        "exportedAt": datetime.utcnow().isoformat(),
        "exportVersion": "1.0",
        "kind": "agent",
        "agents": [agent.model_dump(mode="json")],
        "tools": referenced_tools,
    }


# ── Import preview ─────────────────────────────────────────────────────────

@router.post("/import/preview")
async def preview_agent_import(payload: dict = Body(...)):
    if "agents" not in payload or not isinstance(payload["agents"], list):
        raise HTTPException(status_code=400, detail="Invalid export file: missing 'agents'")
    return {
        "exportId": payload.get("exportId"),
        "agents": [
            {**a, "_status": "exists" if a.get("id") in agents_db else "new"}
            for a in payload["agents"]
        ],
        "tools": [
            {**t, "_status": "exists" if t.get("id") in tools_db else "new"}
            for t in payload.get("tools", [])
        ],
    }


# ── Import apply ───────────────────────────────────────────────────────────

class AgentImportApply(BaseModel):
    export_data: Dict[str, Any]
    decisions: Dict[str, Any]  # { "agents": {id:action}, "tools": {id:action} }


@router.post("/import/apply")
async def apply_agent_import(payload: AgentImportApply):
    data = payload.export_data
    decisions = payload.decisions or {}
    results: Dict[str, list] = {"added": [], "updated": [], "skipped": [], "errors": []}

    def _rec(bucket: str, etype: str, eid: str, ename: str):
        results[bucket].append({"type": etype, "id": eid, "name": ename})

    changed = False

    # Tools first so agent references resolve
    for td in data.get("tools", []):
        action = decisions.get("tools", {}).get(td["id"], "skip")
        if action == "skip":
            _rec("skipped", "tool", td["id"], td.get("name", "")); continue
        existing = td["id"] in tools_db
        if action == "add" and existing:
            _rec("skipped", "tool", td["id"], td.get("name", "")); continue
        try:
            tool = Tool(
                id=td["id"], name=td["name"], description=td["description"],
                type=ToolType(td["type"]), properties=td.get("properties", {}),
                icon=td.get("icon", "wrench"),
                review_status=td.get("review_status", "approved"),
            )
            tools_db[tool.id] = tool
            changed = True
            _rec("updated" if existing else "added", "tool", tool.id, tool.name)
        except Exception as exc:
            results["errors"].append({"type": "tool", "id": td.get("id", ""), "name": td.get("name", ""), "error": str(exc)})

    # Agents
    for ad in data.get("agents", []):
        action = decisions.get("agents", {}).get(ad["id"], "skip")
        if action == "skip":
            _rec("skipped", "agent", ad["id"], ad.get("name", "")); continue
        existing = ad["id"] in agents_db
        if action == "add" and existing:
            _rec("skipped", "agent", ad["id"], ad.get("name", "")); continue
        try:
            agent = Agent(
                id=ad["id"], name=ad["name"], description=ad["description"],
                type=AgentType(ad["type"]),
                tools=ad.get("tools", []),
                tool_configs=ad.get("tool_configs", {}),
                properties=ad.get("properties", {}),
                icon=ad.get("icon", "bot"),
                color=ad.get("color", "#6366f1"),
                review_status=ad.get("review_status", "approved"),
                invoke=ad.get("invoke", {}),
            )
            agents_db[agent.id] = agent
            changed = True
            _rec("updated" if existing else "added", "agent", agent.id, agent.name)
        except Exception as exc:
            results["errors"].append({"type": "agent", "id": ad.get("id", ""), "name": ad.get("name", ""), "error": str(exc)})

    if changed:
        _save_library()
    return results
