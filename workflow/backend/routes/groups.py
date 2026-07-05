"""Group management endpoints."""
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Optional

from models import Group, GroupCreate, GroupUpdate, AuditLog
from db import groups_db, users_db, audit_logs
from routes.auth import require_identity_manager
from portal_persistence import save_portal_data

router = APIRouter()


def _log(actor, action, resource_id, resource_name, details=None):
    audit_logs.append(AuditLog(
        user_id=actor.id, user_email=actor.email, user_name=actor.name,
        action=action, resource_type="group",
        resource_id=resource_id, resource_name=resource_name,
        details=details or {},
    ))


@router.get("/", response_model=List[Group])
def list_groups(
    search: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    actor=Depends(require_identity_manager),
):
    groups = list(groups_db.values())
    if search:
        s = search.lower()
        groups = [g for g in groups if s in g.name.lower()]
    if is_active is not None:
        groups = [g for g in groups if g.is_active == is_active]
    return groups


@router.post("/", response_model=Group)
def create_group(payload: GroupCreate, actor=Depends(require_identity_manager)):
    if any(g.name.lower() == payload.name.lower() for g in groups_db.values()):
        raise HTTPException(status_code=400, detail="Group name already exists")
    group = Group(
        name=payload.name,
        description=payload.description,
        user_ids=payload.user_ids,
        project_ids=payload.project_ids,
    )
    groups_db[group.id] = group
    # sync users
    for uid in payload.user_ids:
        if uid in users_db and group.id not in users_db[uid].group_ids:
            users_db[uid].group_ids.append(group.id)
    _log(actor, "create", group.id, group.name)
    save_portal_data()
    return group


@router.get("/{group_id}", response_model=Group)
def get_group(group_id: str, actor=Depends(require_identity_manager)):
    g = groups_db.get(group_id)
    if not g:
        raise HTTPException(status_code=404, detail="Group not found")
    return g


@router.put("/{group_id}", response_model=Group)
def update_group(group_id: str, payload: GroupUpdate, actor=Depends(require_identity_manager)):
    g = groups_db.get(group_id)
    if not g:
        raise HTTPException(status_code=404, detail="Group not found")
    if payload.name is not None:
        g.name = payload.name
    if payload.description is not None:
        g.description = payload.description
    if payload.user_ids is not None:
        g.user_ids = payload.user_ids
    if payload.project_ids is not None:
        g.project_ids = payload.project_ids
    if payload.is_active is not None:
        g.is_active = payload.is_active
    g.updated_at = datetime.utcnow()
    _log(actor, "update", g.id, g.name)
    save_portal_data()
    return g


@router.delete("/{group_id}")
def delete_group(group_id: str, actor=Depends(require_identity_manager)):
    g = groups_db.pop(group_id, None)
    if not g:
        raise HTTPException(status_code=404, detail="Group not found")
    # remove from users
    for uid in g.user_ids:
        if uid in users_db and group_id in users_db[uid].group_ids:
            users_db[uid].group_ids.remove(group_id)
    _log(actor, "delete", group_id, g.name)
    save_portal_data()
    return {"message": "deleted"}


@router.post("/{group_id}/members/{user_id}", response_model=Group)
def add_member(group_id: str, user_id: str, actor=Depends(require_identity_manager)):
    g = groups_db.get(group_id)
    if not g:
        raise HTTPException(status_code=404, detail="Group not found")
    if user_id not in users_db:
        raise HTTPException(status_code=404, detail="User not found")
    if user_id not in g.user_ids:
        g.user_ids.append(user_id)
    if group_id not in users_db[user_id].group_ids:
        users_db[user_id].group_ids.append(group_id)
    g.updated_at = datetime.utcnow()
    save_portal_data()
    return g


@router.delete("/{group_id}/members/{user_id}", response_model=Group)
def remove_member(group_id: str, user_id: str, actor=Depends(require_identity_manager)):
    g = groups_db.get(group_id)
    if not g:
        raise HTTPException(status_code=404, detail="Group not found")
    if user_id in g.user_ids:
        g.user_ids.remove(user_id)
    if user_id in users_db and group_id in users_db[user_id].group_ids:
        users_db[user_id].group_ids.remove(group_id)
    g.updated_at = datetime.utcnow()
    save_portal_data()
    return g
