"""User management endpoints."""
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Optional

from models import UserOut, UserCreate, UserUpdate, UserInDB, AuditLog, _hash_password
from db import users_db, groups_db, projects_db, audit_logs
from routes.auth import get_current_user, require_identity_manager
from portal_persistence import save_portal_data

router = APIRouter()


def _user_to_out(u) -> UserOut:
    return UserOut(
        id=u.id, email=u.email, name=u.name, role=u.role,
        group_ids=u.group_ids, project_ids=u.project_ids,
        is_active=u.is_active, avatar=u.avatar,
        created_at=u.created_at, updated_at=u.updated_at,
    )


def _log(actor, action, resource_id, resource_name, resource_type="user", details=None):
    audit_logs.append(AuditLog(
        user_id=actor.id, user_email=actor.email, user_name=actor.name,
        action=action, resource_type=resource_type,
        resource_id=resource_id, resource_name=resource_name,
        details=details or {},
    ))


@router.get("/", response_model=List[UserOut])
def list_users(
    search: Optional[str] = Query(None),
    role: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    actor=Depends(require_identity_manager),
):
    users = list(users_db.values())
    if search:
        s = search.lower()
        users = [u for u in users if s in u.name.lower() or s in u.email.lower()]
    if role:
        users = [u for u in users if u.role == role]
    if is_active is not None:
        users = [u for u in users if u.is_active == is_active]
    return [_user_to_out(u) for u in users]


@router.post("/", response_model=UserOut)
def create_user(payload: UserCreate, actor=Depends(require_identity_manager)):
    if any(u.email.lower() == payload.email.lower() for u in users_db.values()):
        raise HTTPException(status_code=400, detail="Email already exists")
    user = UserInDB(
        email=payload.email,
        name=payload.name,
        password_hash=_hash_password(payload.password),
        role=payload.role,
        group_ids=payload.group_ids,
        project_ids=payload.project_ids,
    )
    users_db[user.id] = user
    # sync to project membership
    for pid in payload.project_ids:
        if pid in projects_db and user.id not in projects_db[pid].user_ids:
            projects_db[pid].user_ids.append(user.id)
    _log(actor, "create", user.id, user.email)
    save_portal_data()
    return _user_to_out(user)


@router.get("/{user_id}", response_model=UserOut)
def get_user(user_id: str, actor=Depends(get_current_user)):
    if actor.id != user_id and actor.role not in ("product_admin", "process_admin", "cust_admin"):
        raise HTTPException(status_code=403, detail="Forbidden")
    u = users_db.get(user_id)
    if not u:
        raise HTTPException(status_code=404, detail="User not found")
    return _user_to_out(u)


@router.put("/{user_id}", response_model=UserOut)
def update_user(user_id: str, payload: UserUpdate, actor=Depends(require_identity_manager)):
    u = users_db.get(user_id)
    if not u:
        raise HTTPException(status_code=404, detail="User not found")
    if payload.name is not None:
        u.name = payload.name
    if payload.role is not None:
        u.role = payload.role
    if payload.group_ids is not None:
        u.group_ids = payload.group_ids
    if payload.project_ids is not None:
        u.project_ids = payload.project_ids
    if payload.is_active is not None:
        u.is_active = payload.is_active
    u.updated_at = datetime.utcnow()
    _log(actor, "update", u.id, u.email)
    save_portal_data()
    return _user_to_out(u)


@router.delete("/{user_id}")
def delete_user(user_id: str, actor=Depends(require_identity_manager)):
    u = users_db.pop(user_id, None)
    if not u:
        raise HTTPException(status_code=404, detail="User not found")
    _log(actor, "delete", user_id, u.email)
    save_portal_data()
    return {"message": "deleted"}


@router.patch("/{user_id}/status", response_model=UserOut)
def toggle_status(user_id: str, is_active: bool, actor=Depends(require_identity_manager)):
    u = users_db.get(user_id)
    if not u:
        raise HTTPException(status_code=404, detail="User not found")
    u.is_active = is_active
    u.updated_at = datetime.utcnow()
    _log(actor, "update", u.id, u.email, details={"is_active": is_active})
    save_portal_data()
    return _user_to_out(u)


@router.patch("/{user_id}/password")
def change_password(user_id: str, new_password: str, actor=Depends(require_identity_manager)):
    u = users_db.get(user_id)
    if not u:
        raise HTTPException(status_code=404, detail="User not found")
    u.password_hash = _hash_password(new_password)
    u.updated_at = datetime.utcnow()
    save_portal_data()
    return {"message": "password updated"}
