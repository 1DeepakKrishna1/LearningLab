"""Authentication endpoints: login, logout, current user."""
import uuid
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from models import LoginRequest, LoginResponse, UserOut, _hash_password
from db import users_db, sessions_db, audit_logs
from models import AuditLog

router = APIRouter()
_bearer = HTTPBearer(auto_error=False)


def _user_to_out(u) -> UserOut:
    return UserOut(
        id=u.id, email=u.email, name=u.name, role=u.role,
        group_ids=u.group_ids, project_ids=u.project_ids,
        is_active=u.is_active, avatar=u.avatar,
        created_at=u.created_at, updated_at=u.updated_at,
    )


def get_current_user(creds: HTTPAuthorizationCredentials = Depends(_bearer)):
    if not creds:
        raise HTTPException(status_code=401, detail="Not authenticated")
    user_id = sessions_db.get(creds.credentials)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    user = users_db.get(user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or inactive")
    return user


def require_admin(user=Depends(get_current_user)):
    if user.role not in ("product_admin", "process_admin"):
        raise HTTPException(status_code=403, detail="Admin access required")
    return user


def require_audit_reader(user=Depends(get_current_user)):
    """Allows admins + cust_admin to read audit logs."""
    if user.role not in ("product_admin", "process_admin", "cust_admin"):
        raise HTTPException(status_code=403, detail="Access denied")
    return user


def require_identity_manager(user=Depends(get_current_user)):
    """Allows admins + cust_admin to manage users/groups."""
    if user.role not in ("product_admin", "process_admin", "cust_admin"):
        raise HTTPException(status_code=403, detail="Access denied")
    return user


def require_product_admin(user=Depends(get_current_user)):
    if user.role != "product_admin":
        raise HTTPException(status_code=403, detail="Product admin access required")
    return user


@router.post("/login", response_model=LoginResponse)
def login(req: LoginRequest):
    user = next((u for u in users_db.values() if u.email.lower() == req.email.lower()), None)
    if not user or user.password_hash != _hash_password(req.password):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is inactive")
    token = str(uuid.uuid4())
    sessions_db[token] = user.id
    audit_logs.append(AuditLog(
        user_id=user.id, user_email=user.email, user_name=user.name,
        action="login", resource_type="auth", resource_id=user.id,
        resource_name=user.email,
    ))
    return LoginResponse(token=token, user=_user_to_out(user))


@router.post("/logout")
def logout(creds: HTTPAuthorizationCredentials = Depends(_bearer)):
    if creds and creds.credentials in sessions_db:
        user_id = sessions_db.pop(creds.credentials)
        user = users_db.get(user_id)
        if user:
            audit_logs.append(AuditLog(
                user_id=user.id, user_email=user.email, user_name=user.name,
                action="logout", resource_type="auth", resource_id=user.id,
                resource_name=user.email,
            ))
    return {"message": "ok"}


@router.get("/me", response_model=UserOut)
def me(user=Depends(get_current_user)):
    return _user_to_out(user)
