"""Allocation engine: assigns finite options to applications by merit + preference."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    Allocation,
    AllocationOption,
    Application,
    ApplicationStatus,
    Preference,
    System,
)


def run_allocation(db: Session, system: System, actor_id: int | None = None,
                   round_no: int = 1) -> dict:
    """Capacity-aware allocation.

    - merit_preference: candidates in rank order get their highest-priority
      preference that still has capacity.
    - merit_priority: candidates in rank order fill options in option order
      (used for funds/subsidies where preference is irrelevant).
    """
    cfg = system.config or {}
    strategy = cfg.get("allocation", {}).get("strategy", "merit_preference")

    options = db.scalars(
        select(AllocationOption).where(AllocationOption.system_id == system.id)
    ).all()
    opt_by_key = {o.key: o for o in options}

    # Reset capacities for a fresh run of this round.
    for o in options:
        o.filled = 0
    db.execute(
        Allocation.__table__.delete().where(
            Allocation.application_id.in_(
                select(Application.id).where(Application.system_id == system.id)
            ),
            Allocation.round == round_no,
        )
    )

    ranked = db.scalars(
        select(Application)
        .where(
            Application.system_id == system.id,
            Application.rank.isnot(None),
            Application.status.in_(
                [ApplicationStatus.ranked, ApplicationStatus.allocated,
                 ApplicationStatus.enrolled]
            ),
        )
        .order_by(Application.rank.asc())
    ).all()

    allotted, waitlisted = 0, 0
    for app in ranked:
        chosen: AllocationOption | None = None
        if strategy == "merit_priority":
            for o in options:
                if o.filled < o.capacity:
                    chosen = o
                    break
        else:  # merit_preference
            prefs = db.scalars(
                select(Preference)
                .where(Preference.application_id == app.id)
                .order_by(Preference.priority.asc())
            ).all()
            pref_keys = [p.option_key for p in prefs] or list(opt_by_key.keys())
            for k in pref_keys:
                o = opt_by_key.get(k)
                if o and o.filled < o.capacity:
                    chosen = o
                    break

        if chosen:
            chosen.filled += 1
            db.add(
                Allocation(
                    application_id=app.id,
                    option_key=chosen.key,
                    option_label=chosen.label,
                    round=round_no,
                    status="allotted",
                    allocated_by=actor_id,
                )
            )
            app.status = ApplicationStatus.allocated
            allotted += 1
        else:
            waitlisted += 1

    db.commit()
    return {
        "round": round_no,
        "strategy": strategy,
        "allotted": allotted,
        "waitlisted": waitlisted,
        "options": [
            {"key": o.key, "label": o.label, "capacity": o.capacity, "filled": o.filled}
            for o in options
        ],
    }
