import uuid
from datetime import datetime
from typing import List, Dict, Any
from fastapi import APIRouter, HTTPException, Body
from pydantic import BaseModel

from models import (
    Workflow, Agent, AgentType, Tool, ToolType,
    WorkflowNode, WorkflowEdge, NodePosition, WorkflowStatus,
)
from db import workflows_db, agents_db, tools_db, library_workflow_ids

router = APIRouter()


@router.get("/workflows", response_model=List[Workflow])
async def list_library_workflows():
    return [workflows_db[wid] for wid in library_workflow_ids if wid in workflows_db]


@router.post("/workflows/{workflow_id}/clone", response_model=Workflow)
async def clone_workflow(workflow_id: str):
    if workflow_id not in workflows_db:
        raise HTTPException(status_code=404, detail="Workflow not found")
    original = workflows_db[workflow_id]

    # Remap node IDs so edges remain consistent
    id_map = {n.id: f"node-{str(uuid.uuid4())[:8]}" for n in original.nodes}

    cloned_nodes = [
        WorkflowNode(
            id=id_map[n.id],
            agent_id=n.agent_id,
            position=n.position,
            data=dict(n.data),
        )
        for n in original.nodes
    ]
    cloned_edges = [
        WorkflowEdge(
            id=f"edge-{str(uuid.uuid4())[:8]}",
            source=id_map.get(e.source, e.source),
            target=id_map.get(e.target, e.target),
            label=e.label,
        )
        for e in original.edges
    ]

    cloned = Workflow(
        id=str(uuid.uuid4()),
        name=f"{original.name} (Clone)",
        description=original.description,
        status="draft",
        nodes=cloned_nodes,
        edges=cloned_edges,
        is_template=False,
        tags=list(original.tags),
    )
    workflows_db[cloned.id] = cloned
    return cloned


@router.get("/agents", response_model=List[Agent])
async def list_library_agents():
    return list(agents_db.values())


def _save_library():
    from library_persistence import save_library_data
    save_library_data()


# ── Template Export ────────────────────────────────────────────────────────

@router.get("/workflows/{workflow_id}/export")
async def export_template(workflow_id: str):
    if workflow_id not in workflows_db:
        raise HTTPException(status_code=404, detail="Workflow not found")
    wf = workflows_db[workflow_id]

    # Collect referenced agents and tools
    agent_ids: set = set()
    tool_ids: set = set()
    for node in wf.nodes:
        if node.agent_id:
            agent_ids.add(node.agent_id)
        if node.tool_id:
            tool_ids.add(node.tool_id)

    export_agents = []
    for aid in agent_ids:
        if aid in agents_db:
            export_agents.append(agents_db[aid].model_dump(mode="json"))
            for tid in agents_db[aid].tools:
                tool_ids.add(tid)

    export_tools = [
        tools_db[tid].model_dump(mode="json")
        for tid in tool_ids if tid in tools_db
    ]

    return {
        "exportId": str(uuid.uuid4()),
        "exportedAt": datetime.utcnow().isoformat(),
        "exportVersion": "1.0",
        "kind": "template",
        "workflows": [wf.model_dump(mode="json")],
        "agents": export_agents,
        "tools": export_tools,
    }


# ── Template Import preview ────────────────────────────────────────────────

@router.post("/workflows/import/preview")
async def preview_template_import(payload: dict = Body(...)):
    if "workflows" not in payload or not isinstance(payload["workflows"], list):
        raise HTTPException(status_code=400, detail="Invalid export file: missing 'workflows'")
    return {
        "exportId": payload.get("exportId"),
        "workflows": [
            {**w, "_status": "exists" if w.get("id") in workflows_db else "new"}
            for w in payload["workflows"]
        ],
        "agents": [
            {**a, "_status": "exists" if a.get("id") in agents_db else "new"}
            for a in payload.get("agents", [])
        ],
        "tools": [
            {**t, "_status": "exists" if t.get("id") in tools_db else "new"}
            for t in payload.get("tools", [])
        ],
    }


# ── Template Import apply ──────────────────────────────────────────────────

class TemplateImportApply(BaseModel):
    export_data: Dict[str, Any]
    decisions: Dict[str, Any]
    # decisions: { "workflows": {id:action}, "agents": {id:action}, "tools": {id:action} }


@router.post("/workflows/import/apply")
async def apply_template_import(payload: TemplateImportApply):
    data = payload.export_data
    decisions = payload.decisions or {}
    results: Dict[str, list] = {"added": [], "updated": [], "skipped": [], "errors": []}

    def _rec(bucket: str, etype: str, eid: str, ename: str):
        results[bucket].append({"type": etype, "id": eid, "name": ename})

    changed = False

    # Tools first
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

    # Workflow templates
    for wd in data.get("workflows", []):
        action = decisions.get("workflows", {}).get(wd["id"], "skip")
        if action == "skip":
            _rec("skipped", "template", wd["id"], wd.get("name", "")); continue
        existing = wd["id"] in workflows_db
        if action == "add" and existing:
            _rec("skipped", "template", wd["id"], wd.get("name", "")); continue
        try:
            nodes = [
                WorkflowNode(
                    id=n["id"], node_kind=n.get("node_kind", "agent"),
                    agent_id=n.get("agent_id"), tool_id=n.get("tool_id"),
                    position=NodePosition(**n["position"]), data=n.get("data", {}),
                )
                for n in wd.get("nodes", [])
            ]
            edges = [
                WorkflowEdge(
                    id=e["id"], source=e["source"], target=e["target"],
                    label=e.get("label"), type=e.get("type", "smoothstep"),
                )
                for e in wd.get("edges", [])
            ]
            wf = Workflow(
                id=wd["id"], name=wd["name"], description=wd["description"],
                status=WorkflowStatus(wd.get("status", "draft")),
                nodes=nodes, edges=edges,
                is_template=True,
                tags=wd.get("tags", []),
            )
            workflows_db[wf.id] = wf
            library_workflow_ids.add(wf.id)
            changed = True
            _rec("updated" if existing else "added", "template", wf.id, wf.name)
        except Exception as exc:
            results["errors"].append({"type": "template", "id": wd.get("id", ""), "name": wd.get("name", ""), "error": str(exc)})

    if changed:
        _save_library()
    return results
