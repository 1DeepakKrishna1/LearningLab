"""Role listing endpoints (RBAC reference data)."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select

from app.core.deps import DbSession, require_admin
from app.models import Role
from app.schemas.user import RoleOut

router = APIRouter(prefix="/roles", tags=["Roles"])


@router.get("", response_model=list[RoleOut], dependencies=[Depends(require_admin)])
def list_roles(db: DbSession):
    return list(db.scalars(select(Role).order_by(Role.id)))
