from __future__ import annotations

from collections import Counter

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.core.database import get_db
from app.models import (
    AllocationOption,
    Application,
    AuditLog,
    System,
    User,
    UserRole,
)
from app.schemas.schemas import AuditOut, OptionOut, SystemReport

router = APIRouter(prefix="/api/systems/{system_id}/reports", tags=["reports"])

REPORT_ROLES = (
    UserRole.reporting_authority, UserRole.auditor, UserRole.system_admin,
    UserRole.product_admin, UserRole.allocation_authority,
)


def _guard(system_id: int, user: User, db: Session) -> System:
    system = db.get(System, system_id)
    if not system:
        raise HTTPException(status_code=404, detail="System not found")
    if user.role != UserRole.product_admin and user.system_id != system.id:
        raise HTTPException(status_code=403, detail="Not your system")
    return system


@router.get("/summary", response_model=SystemReport)
def summary(system_id: int, user: User = Depends(require_roles(*REPORT_ROLES)),
            db: Session = Depends(get_db)):
    system = _guard(system_id, user, db)
    apps = db.scalars(
        select(Application).where(Application.system_id == system.id)
    ).all()
    by_status = Counter(a.status.value for a in apps)
    options = db.scalars(
        select(AllocationOption).where(AllocationOption.system_id == system.id)
    ).all()
    capacity = sum(o.capacity for o in options) or 0
    filled = sum(o.filled for o in options)
    fill_rate = round((filled / capacity * 100.0), 2) if capacity else 0.0
    return SystemReport(
        system_id=system.id,
        total_applications=len(apps),
        by_status=dict(by_status),
        options=[OptionOut.model_validate(o) for o in options],
        fill_rate=fill_rate,
    )


@router.get("/audit", response_model=list[AuditOut])
def audit_trail(system_id: int, user: User = Depends(require_roles(*REPORT_ROLES)),
                db: Session = Depends(get_db)):
    _guard(system_id, user, db)
    return db.scalars(
        select(AuditLog).where(AuditLog.system_id == system_id)
        .order_by(AuditLog.created_at.desc()).limit(200)
    ).all()
