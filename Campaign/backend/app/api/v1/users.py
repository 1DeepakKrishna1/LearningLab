"""User management endpoints (admin) and self-profile."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select

from app.core.audit import record_audit
from app.core.deps import CurrentUser, DbSession, require_admin
from app.core.security import hash_password
from app.models import Role, User
from app.schemas.common import Message
from app.schemas.user import RoleOut, UserCreate, UserOut, UserProfileUpdate, UserUpdate

router = APIRouter(prefix="/users", tags=["Users"])


def _assign_roles(db, user: User, role_names: list[str]) -> None:
    roles = list(db.scalars(select(Role).where(Role.name.in_(role_names))))
    if len(roles) != len(set(role_names)):
        found = {r.name for r in roles}
        missing = set(role_names) - found
        raise HTTPException(status_code=400, detail=f"Unknown roles: {', '.join(missing)}")
    user.roles = roles


@router.get("", response_model=list[UserOut], dependencies=[Depends(require_admin)])
def list_users(db: DbSession):
    return list(db.scalars(select(User).order_by(User.id)))


@router.post("", response_model=UserOut, status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(require_admin)])
def create_user(db: DbSession, payload: UserCreate, actor: CurrentUser):
    if db.scalar(select(User).where(User.email == payload.email.lower())):
        raise HTTPException(status_code=409, detail="Email already registered")
    user = User(
        email=payload.email.lower(),
        full_name=payload.full_name,
        hashed_password=hash_password(payload.password),
    )
    _assign_roles(db, user, payload.roles)
    db.add(user)
    db.commit()
    db.refresh(user)
    record_audit(db, action="user.create", user=actor, entity_type="user", entity_id=user.id)
    return user


@router.get("/{user_id}", response_model=UserOut, dependencies=[Depends(require_admin)])
def get_user(db: DbSession, user_id: int):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.patch("/{user_id}", response_model=UserOut, dependencies=[Depends(require_admin)])
def update_user(db: DbSession, user_id: int, payload: UserUpdate, actor: CurrentUser):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if payload.full_name is not None:
        user.full_name = payload.full_name
    if payload.is_active is not None:
        user.is_active = payload.is_active
    if payload.roles is not None:
        _assign_roles(db, user, payload.roles)
    db.commit()
    db.refresh(user)
    record_audit(db, action="user.update", user=actor, entity_type="user", entity_id=user.id)
    return user


@router.delete("/{user_id}", response_model=Message, dependencies=[Depends(require_admin)])
def delete_user(db: DbSession, user_id: int, actor: CurrentUser):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.id == actor.id:
        raise HTTPException(status_code=400, detail="You cannot delete your own account")
    db.delete(user)
    db.commit()
    record_audit(db, action="user.delete", user=actor, entity_type="user", entity_id=user_id)
    return Message(message="User deleted")


@router.patch("/me/profile", response_model=UserOut)
def update_my_profile(db: DbSession, user: CurrentUser, payload: UserProfileUpdate):
    if payload.full_name is not None:
        user.full_name = payload.full_name
    db.commit()
    db.refresh(user)
    return user
