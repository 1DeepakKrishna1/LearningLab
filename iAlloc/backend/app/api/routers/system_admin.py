from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_system_admin
from app.core.database import get_db
from app.core.security import hash_password
from app.models import (
    STAKEHOLDER_ROLES,
    AllocationOption,
    System,
    User,
    UserRole,
)
from app.schemas.schemas import (
    OptionCreate,
    OptionOut,
    StageConfigUpdate,
    SystemOut,
    UserCreate,
    UserOut,
)
from app.services.config_builder import load_catalog
from app.services.workflow import audit

router = APIRouter(prefix="/api/systems/{system_id}/admin", tags=["system-admin"])


@router.get("/config", response_model=SystemOut)
def get_config(system_id: int, system: System = Depends(require_system_admin)):
    return system


@router.get("/catalog")
def stage_catalog(system_id: int, _: System = Depends(require_system_admin)):
    """Expose the stage/AI-task catalog so admins know what they can enable."""
    cat = load_catalog()
    return {
        "stage_catalog": cat["stage_catalog"],
        "ai_task_prompts": cat["ai_task_prompts"],
    }


def _save_config(db: Session, system: System, config: dict, actor_id: int, action: str):
    system.config = config
    audit(db, system_id=system.id, actor_id=actor_id, action=action,
          entity_type="system", entity_id=system.id)
    db.commit()
    db.refresh(system)


@router.patch("/stages/{stage_key}", response_model=SystemOut)
def update_stage(
    system_id: int, stage_key: str, body: StageConfigUpdate,
    system: System = Depends(require_system_admin), db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    config = dict(system.config or {})
    stages = list(config.get("stages", []))
    target = next((s for s in stages if s["key"] == stage_key), None)
    if target is None:
        raise HTTPException(status_code=404, detail="Stage not found")

    if body.name is not None:
        target["name"] = body.name
    if body.enabled is not None:
        target["enabled"] = body.enabled
    if body.roles is not None:
        target["roles"] = body.roles
    if body.ai is not None:
        target["ai"] = {
            "enabled": body.ai.enabled,
            "task": body.ai.task,
            "model": body.ai.model,
            "instructions": body.ai.instructions,
        }
    config["stages"] = stages
    _save_config(db, system, config, user.id, "stage_updated")
    return system


@router.patch("/stages/{stage_key}/ai", response_model=SystemOut)
def toggle_stage_ai(
    system_id: int, stage_key: str, enabled: bool,
    system: System = Depends(require_system_admin), db: Session = Depends(get_db),
):
    config = dict(system.config or {})
    stages = list(config.get("stages", []))
    target = next((s for s in stages if s["key"] == stage_key), None)
    if target is None:
        raise HTTPException(status_code=404, detail="Stage not found")
    ai = dict(target.get("ai", {}))
    ai["enabled"] = enabled
    target["ai"] = ai
    config["stages"] = stages
    _save_config(db, system, config, None, "stage_ai_toggled")
    return system


# --------------------------- Allocation options --------------------------- #
@router.get("/options", response_model=list[OptionOut])
def list_options(system_id: int, system: System = Depends(require_system_admin),
                 db: Session = Depends(get_db)):
    return db.scalars(
        select(AllocationOption).where(AllocationOption.system_id == system.id)
    ).all()


@router.post("/options", response_model=OptionOut, status_code=201)
def add_option(system_id: int, body: OptionCreate,
               system: System = Depends(require_system_admin),
               db: Session = Depends(get_db)):
    opt = AllocationOption(
        system_id=system.id, key=body.key, label=body.label,
        capacity=body.capacity, meta=body.meta,
    )
    db.add(opt)
    db.commit()
    db.refresh(opt)
    return opt


@router.delete("/options/{option_id}", status_code=204)
def delete_option(system_id: int, option_id: int,
                  system: System = Depends(require_system_admin),
                  db: Session = Depends(get_db)):
    opt = db.get(AllocationOption, option_id)
    if not opt or opt.system_id != system.id:
        raise HTTPException(status_code=404, detail="Option not found")
    db.delete(opt)
    db.commit()


# --------------------------- Stakeholder management --------------------------- #
@router.get("/members", response_model=list[UserOut])
def members(system_id: int, system: System = Depends(require_system_admin),
            db: Session = Depends(get_db)):
    return db.scalars(select(User).where(User.system_id == system.id)).all()


@router.post("/members", response_model=UserOut, status_code=201)
def add_member(
    system_id: int, body: UserCreate,
    system: System = Depends(require_system_admin), db: Session = Depends(get_db),
):
    if body.role not in STAKEHOLDER_ROLES and body.role != UserRole.system_admin:
        raise HTTPException(status_code=400, detail="Invalid role for a system member")
    if db.scalar(select(User).where(User.email == body.email)):
        raise HTTPException(status_code=409, detail="Email already registered")
    member = User(
        email=body.email,
        full_name=body.full_name,
        hashed_password=hash_password(body.password),
        role=body.role,
        system_id=system.id,
    )
    db.add(member)
    db.commit()
    db.refresh(member)
    return member


@router.patch("/members/{user_id}/active", response_model=UserOut)
def set_member_active(system_id: int, user_id: int, active: bool,
                      system: System = Depends(require_system_admin),
                      db: Session = Depends(get_db)):
    member = db.get(User, user_id)
    if not member or member.system_id != system.id:
        raise HTTPException(status_code=404, detail="Member not found")
    member.is_active = active
    db.commit()
    db.refresh(member)
    return member
