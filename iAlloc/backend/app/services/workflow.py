"""Workflow engine helpers: stage initialization, transitions and audit logging."""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    Application,
    AuditLog,
    StageRecord,
    StageStatus,
    System,
)
from app.services.config_builder import ordered_enabled_stages, stage_by_key


def audit(db: Session, *, system_id, actor_id, action, entity_type="",
          entity_id=None, detail=None) -> None:
    db.add(
        AuditLog(
            system_id=system_id,
            actor_id=actor_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            detail=detail or {},
        )
    )


def init_stage_records(db: Session, application: Application, system: System) -> None:
    """Create a pending StageRecord for every enabled stage of the system."""
    stages = ordered_enabled_stages(system.config or {})
    existing = {
        r.stage_key
        for r in db.scalars(
            select(StageRecord).where(StageRecord.application_id == application.id)
        ).all()
    }
    for s in stages:
        if s["key"] in existing:
            continue
        db.add(StageRecord(application_id=application.id, stage_key=s["key"]))
    if stages and not application.current_stage_key:
        application.current_stage_key = stages[0]["key"]
        first = next(
            (r for r in application.stage_records if r.stage_key == stages[0]["key"]),
            None,
        )


def get_stage_record(db: Session, application_id: int, stage_key: str) -> StageRecord | None:
    return db.scalar(
        select(StageRecord).where(
            StageRecord.application_id == application_id,
            StageRecord.stage_key == stage_key,
        )
    )


def complete_stage(
    db: Session,
    application: Application,
    system: System,
    stage_key: str,
    *,
    actor_id: int | None,
    data: dict | None = None,
    remarks: str = "",
) -> StageRecord:
    """Mark a stage complete and advance current_stage_key to the next enabled stage."""
    rec = get_stage_record(db, application.id, stage_key)
    if rec is None:
        rec = StageRecord(application_id=application.id, stage_key=stage_key)
        db.add(rec)
    rec.status = StageStatus.completed
    rec.completed_by = actor_id
    rec.completed_at = datetime.now(timezone.utc)
    if data:
        merged = dict(rec.data or {})
        merged.update(data)
        rec.data = merged
    if remarks:
        rec.remarks = remarks

    # Advance pointer
    stages = ordered_enabled_stages(system.config or {})
    keys = [s["key"] for s in stages]
    if stage_key in keys:
        idx = keys.index(stage_key)
        application.current_stage_key = keys[idx + 1] if idx + 1 < len(keys) else stage_key

    audit(
        db,
        system_id=system.id,
        actor_id=actor_id,
        action="stage_completed",
        entity_type="application",
        entity_id=application.id,
        detail={"stage": stage_key, "remarks": remarks},
    )
    return rec


def progress_summary(application: Application, system: System) -> list[dict]:
    """Per-stage progress view for an application."""
    stages = ordered_enabled_stages(system.config or {})
    rec_by_key = {r.stage_key: r for r in application.stage_records}
    out = []
    for s in stages:
        rec = rec_by_key.get(s["key"])
        out.append(
            {
                "key": s["key"],
                "name": s["name"],
                "type": s["type"],
                "order": s["order"],
                "ai_enabled": s.get("ai", {}).get("enabled", False),
                "status": (rec.status.value if rec else "pending"),
                "is_current": application.current_stage_key == s["key"],
                "remarks": rec.remarks if rec else "",
            }
        )
    return out
