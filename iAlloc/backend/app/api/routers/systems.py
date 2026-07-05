from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_system_for_user
from app.core.database import get_db
from app.models import AllocationOption, System, SystemStatus, User
from app.schemas.schemas import OptionOut, SystemOut, SystemSummary
from app.services.config_builder import ordered_enabled_stages

router = APIRouter(prefix="/api/systems", tags=["systems"])


@router.get("/public", response_model=list[SystemSummary])
def public_systems(db: Session = Depends(get_db)):
    """Open list of active systems, used by the registration screen."""
    return db.scalars(
        select(System).where(System.status == SystemStatus.active)
    ).all()


@router.get("/{system_id}", response_model=SystemOut)
def get_system(system_id: int, system: System = Depends(get_system_for_user)):
    return system


@router.get("/{system_id}/stages")
def system_stages(system_id: int, system: System = Depends(get_system_for_user)):
    return ordered_enabled_stages(system.config or {})


@router.get("/{system_id}/options", response_model=list[OptionOut])
def system_options(system_id: int, system: System = Depends(get_system_for_user),
                   db: Session = Depends(get_db)):
    return db.scalars(
        select(AllocationOption).where(AllocationOption.system_id == system.id)
    ).all()


@router.get("/mine/list")
def my_system(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not user.system_id:
        return None
    s = db.get(System, user.system_id)
    if not s:
        return None
    return SystemSummary.model_validate(s).model_dump()
