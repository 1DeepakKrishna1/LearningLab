"""Project management endpoints."""
import uuid as _uuid
import hashlib as _hashlib
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends, Query, Body
from typing import List, Optional, Dict, Any
from pydantic import BaseModel

from models import (
    Project, ProjectCreate, ProjectUpdate, AuditLog,
    Tool, ToolType, Agent, AgentType,
    Workflow, WorkflowNode, WorkflowEdge, NodePosition, WorkflowStatus,
    UserInDB, UserRole,
    DataModel, DataModelEntity, DataModelField, DataModelRelationship, FieldType, RelationType,
    WorkflowAssociation, InputMapping, ActivityBinding, Environment,
)
from db import projects_db, users_db, workflows_db, groups_db, audit_logs, tools_db, agents_db, data_models_db, workflow_associations_db
from routes.auth import get_current_user, require_admin
from portal_persistence import save_portal_data
from persistence import save_user_workflows
from library_persistence import save_library_data
from data_models_persistence import save_data_models, save_associations

router = APIRouter()


def _log(actor, action, resource_id, resource_name, details=None):
    audit_logs.append(AuditLog(
        user_id=actor.id, user_email=actor.email, user_name=actor.name,
        action=action, resource_type="project",
        resource_id=resource_id, resource_name=resource_name,
        details=details or {},
    ))


@router.get("/", response_model=List[Project])
def list_projects(
    search: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    actor=Depends(get_current_user),
):
    projects = list(projects_db.values())
    # org_users only see their assigned projects
    if actor.role == "org_user":
        projects = [p for p in projects if actor.id in p.user_ids]
    if search:
        s = search.lower()
        projects = [p for p in projects if s in p.name.lower()]
    if is_active is not None:
        projects = [p for p in projects if p.is_active == is_active]
    return projects


@router.post("/", response_model=Project)
def create_project(payload: ProjectCreate, actor=Depends(require_admin)):
    project = Project(
        name=payload.name,
        description=payload.description,
        launchurl=payload.launchurl,
        workflow_ids=payload.workflow_ids,
        user_ids=payload.user_ids,
        group_ids=payload.group_ids,
        owner_id=actor.id,
    )
    projects_db[project.id] = project
    # sync users
    for uid in payload.user_ids:
        if uid in users_db and project.id not in users_db[uid].project_ids:
            users_db[uid].project_ids.append(project.id)
    _log(actor, "create", project.id, project.name)
    save_portal_data()
    return project


@router.get("/{project_id}", response_model=Project)
def get_project(project_id: str, actor=Depends(get_current_user)):
    p = projects_db.get(project_id)
    if not p:
        raise HTTPException(status_code=404, detail="Project not found")
    if actor.role == "org_user" and actor.id not in p.user_ids:
        raise HTTPException(status_code=403, detail="Forbidden")
    return p


@router.put("/{project_id}", response_model=Project)
def update_project(project_id: str, payload: ProjectUpdate, actor=Depends(require_admin)):
    p = projects_db.get(project_id)
    if not p:
        raise HTTPException(status_code=404, detail="Project not found")
    if payload.name is not None:
        p.name = payload.name
    if payload.description is not None:
        p.description = payload.description
    if payload.launchurl is not None:
        p.launchurl = payload.launchurl
    if payload.workflow_ids is not None:
        p.workflow_ids = payload.workflow_ids
    if payload.user_ids is not None:
        p.user_ids = payload.user_ids
    if payload.group_ids is not None:
        p.group_ids = payload.group_ids
    if payload.is_active is not None:
        p.is_active = payload.is_active
    p.updated_at = datetime.utcnow()
    _log(actor, "update", p.id, p.name)
    save_portal_data()
    return p


@router.delete("/{project_id}")
def delete_project(project_id: str, actor=Depends(require_admin)):
    p = projects_db.pop(project_id, None)
    if not p:
        raise HTTPException(status_code=404, detail="Project not found")
    # remove from users
    for uid in p.user_ids:
        if uid in users_db and project_id in users_db[uid].project_ids:
            users_db[uid].project_ids.remove(project_id)
    _log(actor, "delete", project_id, p.name)
    save_portal_data()
    return {"message": "deleted"}


@router.post("/{project_id}/workflows/{workflow_id}", response_model=Project)
def add_workflow(project_id: str, workflow_id: str, actor=Depends(require_admin)):
    p = projects_db.get(project_id)
    if not p:
        raise HTTPException(status_code=404, detail="Project not found")
    if workflow_id not in workflows_db:
        raise HTTPException(status_code=404, detail="Workflow not found")
    if workflow_id not in p.workflow_ids:
        p.workflow_ids.append(workflow_id)
    p.updated_at = datetime.utcnow()
    save_portal_data()
    return p


@router.delete("/{project_id}/workflows/{workflow_id}", response_model=Project)
def remove_workflow(project_id: str, workflow_id: str, actor=Depends(require_admin)):
    p = projects_db.get(project_id)
    if not p:
        raise HTTPException(status_code=404, detail="Project not found")
    if workflow_id in p.workflow_ids:
        p.workflow_ids.remove(workflow_id)
    p.updated_at = datetime.utcnow()
    save_portal_data()
    return p


@router.post("/{project_id}/users/{user_id}", response_model=Project)
def add_user(project_id: str, user_id: str, actor=Depends(require_admin)):
    p = projects_db.get(project_id)
    if not p:
        raise HTTPException(status_code=404, detail="Project not found")
    if user_id not in users_db:
        raise HTTPException(status_code=404, detail="User not found")
    if user_id not in p.user_ids:
        p.user_ids.append(user_id)
    if project_id not in users_db[user_id].project_ids:
        users_db[user_id].project_ids.append(project_id)
    p.updated_at = datetime.utcnow()
    save_portal_data()
    return p


@router.delete("/{project_id}/users/{user_id}", response_model=Project)
def remove_user(project_id: str, user_id: str, actor=Depends(require_admin)):
    p = projects_db.get(project_id)
    if not p:
        raise HTTPException(status_code=404, detail="Project not found")
    if user_id in p.user_ids:
        p.user_ids.remove(user_id)
    if user_id in users_db and project_id in users_db[user_id].project_ids:
        users_db[user_id].project_ids.remove(project_id)
    p.updated_at = datetime.utcnow()
    save_portal_data()
    return p


# ── Export ─────────────────────────────────────────────────────────────────

@router.get("/{project_id}/export")
def export_project(project_id: str, actor=Depends(require_admin)):
    p = projects_db.get(project_id)
    if not p:
        raise HTTPException(status_code=404, detail="Project not found")

    # User-created workflows only (no templates)
    project_workflows = [
        workflows_db[wid].model_dump(mode="json")
        for wid in p.workflow_ids
        if wid in workflows_db and not workflows_db[wid].is_template
    ]

    # Gather agent and tool IDs referenced by those workflows
    agent_ids: set = set()
    tool_ids: set = set()
    for wid in p.workflow_ids:
        if wid in workflows_db:
            for node in workflows_db[wid].nodes:
                if node.agent_id:
                    agent_ids.add(node.agent_id)
                if node.tool_id:
                    tool_ids.add(node.tool_id)

    # Collect agents (and their tool references)
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

    # Collect data models and workflow associations for this project's workflows
    wf_id_set = set(p.workflow_ids)
    data_model_ids: set = set()
    export_associations = []
    for assoc in workflow_associations_db.values():
        if assoc.workflow_id in wf_id_set:
            if assoc.data_model_id:
                data_model_ids.add(assoc.data_model_id)
            ad = assoc.model_dump(mode="json")
            wf_name = workflows_db[assoc.workflow_id].name if assoc.workflow_id in workflows_db else assoc.workflow_id
            env_val = assoc.environment.value if hasattr(assoc.environment, "value") else str(assoc.environment)
            ad["name"] = f"{wf_name} ({env_val})"
            export_associations.append(ad)
    export_data_models = [
        data_models_db[dmid].model_dump(mode="json")
        for dmid in data_model_ids if dmid in data_models_db
    ]

    # Users — omit password hash
    export_users = []
    for uid in p.user_ids:
        if uid in users_db:
            ud = users_db[uid].model_dump(mode="json")
            ud["password_hash"] = ""
            export_users.append(ud)

    export_id = str(_uuid.uuid4())
    payload = {
        "exportId": export_id,
        "exportedAt": datetime.utcnow().isoformat(),
        "exportVersion": "1.0",
        "customer": p.model_dump(mode="json"),
        "workflows": project_workflows,
        "users": export_users,
        "agents": export_agents,
        "tools": export_tools,
        "data_models": export_data_models,
        "workflow_associations": export_associations,
    }
    _log(actor, "export", p.id, p.name, {"exportId": export_id})
    return payload


# ── Import preview ─────────────────────────────────────────────────────────

@router.post("/import/preview")
def preview_import(payload: dict = Body(...), actor=Depends(require_admin)):
    for key in ("customer", "workflows", "users", "agents", "tools", "data_models", "workflow_associations"):
        if key not in payload:
            raise HTTPException(status_code=400, detail=f"Invalid export file: missing '{key}'")

    def _status(eid: str, db: dict) -> str:
        return "exists" if eid in db else "new"

    cust = payload["customer"]
    return {
        "exportId": payload.get("exportId"),
        "customer":              {**cust, "_status": _status(cust["id"], projects_db)},
        "workflows":             [{**w,  "_status": _status(w["id"],  workflows_db)}             for w  in payload["workflows"]],
        "users":                 [{**u,  "_status": _status(u["id"],  users_db)}                 for u  in payload["users"]],
        "agents":                [{**a,  "_status": _status(a["id"],  agents_db)}                for a  in payload["agents"]],
        "tools":                 [{**t,  "_status": _status(t["id"],  tools_db)}                 for t  in payload["tools"]],
        "data_models":           [{**dm, "_status": _status(dm["id"], data_models_db)}           for dm in payload["data_models"]],
        "workflow_associations": [{**wa, "_status": _status(wa["id"], workflow_associations_db)} for wa in payload["workflow_associations"]],
    }


# ── Import apply ───────────────────────────────────────────────────────────

class ImportApplyRequest(BaseModel):
    export_data: Dict[str, Any]
    decisions: Dict[str, Any]
    # decisions shape:
    # { "customer": "add"|"update"|"skip",
    #   "workflows": {id: action}, "users": {id: action},
    #   "agents": {id: action}, "tools": {id: action} }


@router.post("/import/apply")
def apply_import(payload: ImportApplyRequest, actor=Depends(require_admin)):
    data = payload.export_data
    decisions = payload.decisions
    results: Dict[str, list] = {"added": [], "updated": [], "skipped": [], "errors": []}

    needs_library = False
    needs_workflows = False
    needs_portal = False
    needs_data_models = False
    needs_associations = False

    def _rec(bucket: str, etype: str, eid: str, ename: str):
        results[bucket].append({"type": etype, "id": eid, "name": ename})

    # action semantics:
    #   "add"    → create only if entity does not yet exist (safe, no overwrite)
    #   "update" → upsert (create or overwrite)
    #   "skip"   → do nothing

    # ── Data Models ────────────────────────────────────
    for dmd in data.get("data_models", []):
        action = decisions.get("data_models", {}).get(dmd["id"], "skip")
        if action == "skip":
            _rec("skipped", "data_model", dmd["id"], dmd.get("name", "")); continue
        existing = dmd["id"] in data_models_db
        if action == "add" and existing:
            _rec("skipped", "data_model", dmd["id"], dmd.get("name", "")); continue
        try:
            entities = [
                DataModelEntity(
                    id=e["id"], name=e["name"], description=e.get("description", ""),
                    fields=[
                        DataModelField(
                            name=f["name"],
                            field_type=FieldType(f.get("field_type", "string")),
                            required=f.get("required", False),
                            description=f.get("description", ""),
                            validation=f.get("validation"),
                            default_value=f.get("default_value"),
                        ) for f in e.get("fields", [])
                    ],
                ) for e in dmd.get("entities", [])
            ]
            relationships = [
                DataModelRelationship(
                    id=r["id"],
                    from_entity=r["from_entity"],
                    to_entity=r["to_entity"],
                    relation_type=RelationType(r.get("relation_type", "one_to_many")),
                    label=r.get("label", ""),
                ) for r in dmd.get("relationships", [])
            ]
            dm = DataModel(
                id=dmd["id"], name=dmd["name"], description=dmd.get("description", ""),
                entities=entities, relationships=relationships,
            )
            data_models_db[dm.id] = dm
            needs_data_models = True
            _rec("updated" if existing else "added", "data_model", dm.id, dm.name)
        except Exception as exc:
            results["errors"].append({"type": "data_model", "id": dmd["id"], "name": dmd.get("name", ""), "error": str(exc)})

    # ── Tools ──────────────────────────────────────────
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
                icon=td.get("icon", "wrench"), review_status=td.get("review_status", "approved"),
            )
            tools_db[tool.id] = tool
            needs_library = True
            _rec("updated" if existing else "added", "tool", tool.id, tool.name)
        except Exception as exc:
            results["errors"].append({"type": "tool", "id": td["id"], "name": td.get("name", ""), "error": str(exc)})

    # ── Agents ─────────────────────────────────────────
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
                type=AgentType(ad["type"]), tools=ad.get("tools", []),
                tool_configs=ad.get("tool_configs", {}), properties=ad.get("properties", {}),
                icon=ad.get("icon", "bot"), color=ad.get("color", "#6366f1"),
                review_status=ad.get("review_status", "approved"),
            )
            agents_db[agent.id] = agent
            needs_library = True
            _rec("updated" if existing else "added", "agent", agent.id, agent.name)
        except Exception as exc:
            results["errors"].append({"type": "agent", "id": ad["id"], "name": ad.get("name", ""), "error": str(exc)})

    # ── Workflows ──────────────────────────────────────
    for wd in data.get("workflows", []):
        action = decisions.get("workflows", {}).get(wd["id"], "skip")
        if action == "skip":
            _rec("skipped", "workflow", wd["id"], wd.get("name", "")); continue
        existing = wd["id"] in workflows_db
        if action == "add" and existing:
            _rec("skipped", "workflow", wd["id"], wd.get("name", "")); continue
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
                nodes=nodes, edges=edges, is_template=False, tags=wd.get("tags", []),
            )
            workflows_db[wf.id] = wf
            needs_workflows = True
            _rec("updated" if existing else "added", "workflow", wf.id, wf.name)
        except Exception as exc:
            results["errors"].append({"type": "workflow", "id": wd["id"], "name": wd.get("name", ""), "error": str(exc)})

    # ── Workflow Associations ──────────────────────────
    for ad in data.get("workflow_associations", []):
        action = decisions.get("workflow_associations", {}).get(ad["id"], "skip")
        if action == "skip":
            _rec("skipped", "workflow_association", ad["id"], ad.get("name", "")); continue
        existing = ad["id"] in workflow_associations_db
        if action == "add" and existing:
            _rec("skipped", "workflow_association", ad["id"], ad.get("name", "")); continue
        try:
            assoc = WorkflowAssociation(
                id=ad["id"],
                workflow_id=ad["workflow_id"],
                data_model_id=ad.get("data_model_id"),
                project=ad.get("project", ""),
                environment=Environment(ad.get("environment", "dev")),
                global_context=ad.get("global_context", {}),
                input_mappings=[InputMapping(**m) for m in ad.get("input_mappings", [])],
                default_values=ad.get("default_values", {}),
                validation_rules=ad.get("validation_rules", []),
                activity_bindings=[ActivityBinding(**b) for b in ad.get("activity_bindings", [])],
            )
            workflow_associations_db[assoc.id] = assoc
            needs_associations = True
            _rec("updated" if existing else "added", "workflow_association", assoc.id, ad.get("name", ""))
        except Exception as exc:
            results["errors"].append({"type": "workflow_association", "id": ad["id"], "name": ad.get("name", ""), "error": str(exc)})

    # ── Users ──────────────────────────────────────────
    for ud in data.get("users", []):
        action = decisions.get("users", {}).get(ud["id"], "skip")
        if action == "skip":
            _rec("skipped", "user", ud["id"], ud.get("name", "")); continue
        existing = ud["id"] in users_db
        if action == "add" and existing:
            _rec("skipped", "user", ud["id"], ud.get("name", "")); continue
        try:
            ph = ud.get("password_hash") or _hashlib.sha256("Imported@123".encode()).hexdigest()
            user = UserInDB(
                id=ud["id"], email=ud["email"], name=ud["name"],
                password_hash=ph, role=UserRole(ud["role"]),
                group_ids=ud.get("group_ids", []), project_ids=ud.get("project_ids", []),
                is_active=ud.get("is_active", True), avatar=ud.get("avatar"),
            )
            users_db[user.id] = user
            needs_portal = True
            _rec("updated" if existing else "added", "user", user.id, user.name)
        except Exception as exc:
            results["errors"].append({"type": "user", "id": ud["id"], "name": ud.get("name", ""), "error": str(exc)})

    # ── Customer (Project) ─────────────────────────────
    cd = data.get("customer", {})
    c_action = decisions.get("customer", "skip")
    if c_action == "skip":
        _rec("skipped", "customer", cd.get("id", ""), cd.get("name", ""))
    else:
        existing = cd.get("id", "") in projects_db
        if c_action == "add" and existing:
            _rec("skipped", "customer", cd.get("id", ""), cd.get("name", ""))
        else:
            try:
                project = Project(
                    id=cd["id"], name=cd["name"], description=cd.get("description", ""),
                    launchurl=cd.get("launchurl"),
                    workflow_ids=cd.get("workflow_ids", []),
                    user_ids=cd.get("user_ids", []),
                    group_ids=cd.get("group_ids", []),
                    owner_id=cd.get("owner_id"),
                    is_active=cd.get("is_active", True),
                )
                projects_db[project.id] = project
                for uid in project.user_ids:
                    if uid in users_db and project.id not in users_db[uid].project_ids:
                        users_db[uid].project_ids.append(project.id)
                needs_portal = True
                _rec("updated" if existing else "added", "customer", project.id, project.name)
            except Exception as exc:
                results["errors"].append({"type": "customer", "id": cd.get("id", ""), "name": cd.get("name", ""), "error": str(exc)})

    # Persist changes
    if needs_data_models:
        save_data_models()
    if needs_associations:
        save_associations()
    if needs_portal:
        save_portal_data()
    if needs_workflows:
        save_user_workflows()
    if needs_library:
        save_library_data()

    _log(actor, "import", cd.get("id", "unknown"), cd.get("name", "unknown"), {
        "exportId": data.get("exportId"),
        "added": len(results["added"]),
        "updated": len(results["updated"]),
        "skipped": len(results["skipped"]),
        "errors": len(results["errors"]),
    })
    return results
