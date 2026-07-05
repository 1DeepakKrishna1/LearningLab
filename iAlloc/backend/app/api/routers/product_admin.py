from __future__ import annotations

import secrets

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_product_admin
from app.core.database import get_db
from app.core.security import hash_password
from app.models import (
    AllocationOption,
    Application,
    System,
    SystemStatus,
    User,
    UserRole,
)
from app.schemas.schemas import (
    DomainTemplate,
    SystemCreate,
    SystemOut,
    SystemSummary,
    SystemUpdate,
    UserOut,
)
from app.services.config_builder import build_config, default_options, list_domains
from app.services.workflow import audit

router = APIRouter(prefix="/api/admin", tags=["product-admin"])


@router.get("/domain-templates", response_model=list[DomainTemplate])
def domain_templates(_: User = Depends(get_product_admin)):
    return list_domains()


@router.get("/systems", response_model=list[SystemSummary])
def list_all_systems(_: User = Depends(get_product_admin), db: Session = Depends(get_db)):
    return db.scalars(select(System).order_by(System.created_at.desc())).all()


@router.post("/systems", response_model=SystemOut, status_code=201)
def create_system(
    body: SystemCreate,
    admin: User = Depends(get_product_admin),
    db: Session = Depends(get_db),
):
    if db.scalar(select(System).where(System.key == body.key)):
        raise HTTPException(status_code=409, detail="System key already exists")

    config = build_config(body.domain.value)
    system = System(
        key=body.key,
        name=body.name,
        domain=body.domain,
        description=body.description,
        status=SystemStatus.draft,
        config=config,
        created_by=admin.id,
    )
    db.add(system)
    db.flush()  # assign id

    # Seed default allocation options for the chosen domain.
    for opt in default_options(body.domain.value):
        db.add(
            AllocationOption(
                system_id=system.id,
                key=opt["key"],
                label=opt["label"],
                capacity=opt.get("capacity", 0),
                meta=opt.get("meta", {}),
            )
        )

    # Provision the SystemAdmin for this system.
    created_admin = None
    if body.system_admin_email:
        if db.scalar(select(User).where(User.email == body.system_admin_email)):
            raise HTTPException(status_code=409, detail="SystemAdmin email already used")
        temp_pw = body.system_admin_password or secrets.token_urlsafe(8)
        created_admin = User(
            email=body.system_admin_email,
            full_name=body.system_admin_name or f"{body.name} Admin",
            hashed_password=hash_password(temp_pw),
            role=UserRole.system_admin,
            system_id=system.id,
        )
        db.add(created_admin)
        system.config = {**system.config, "_provisioned_admin": body.system_admin_email}

    audit(
        db, system_id=system.id, actor_id=admin.id, action="system_created",
        entity_type="system", entity_id=system.id,
        detail={"domain": body.domain.value, "key": body.key},
    )
    db.commit()
    db.refresh(system)
    return system


@router.get("/systems/{system_id}", response_model=SystemOut)
def get_system(system_id: int, _: User = Depends(get_product_admin),
               db: Session = Depends(get_db)):
    system = db.get(System, system_id)
    if not system:
        raise HTTPException(status_code=404, detail="System not found")
    return system


@router.patch("/systems/{system_id}", response_model=SystemOut)
def update_system(
    system_id: int, body: SystemUpdate,
    admin: User = Depends(get_product_admin), db: Session = Depends(get_db),
):
    system = db.get(System, system_id)
    if not system:
        raise HTTPException(status_code=404, detail="System not found")
    if body.name is not None:
        system.name = body.name
    if body.description is not None:
        system.description = body.description
    if body.status is not None:
        system.status = body.status
    if body.config is not None:
        system.config = body.config
    audit(db, system_id=system.id, actor_id=admin.id, action="system_updated",
          entity_type="system", entity_id=system.id)
    db.commit()
    db.refresh(system)
    return system


@router.get("/systems/{system_id}/members", response_model=list[UserOut])
def system_members(system_id: int, _: User = Depends(get_product_admin),
                   db: Session = Depends(get_db)):
    return db.scalars(select(User).where(User.system_id == system_id)).all()


@router.get("/overview")
def overview(_: User = Depends(get_product_admin), db: Session = Depends(get_db)):
    systems = db.scalars(select(System)).all()
    out = []
    for s in systems:
        total = len(db.scalars(select(Application.id).where(Application.system_id == s.id)).all())
        members = len(db.scalars(select(User.id).where(User.system_id == s.id)).all())
        out.append(
            {
                "id": s.id, "key": s.key, "name": s.name,
                "domain": s.domain.value, "status": s.status.value,
                "applications": total, "members": members,
            }
        )
    return {"systems": out, "total_systems": len(systems)}
