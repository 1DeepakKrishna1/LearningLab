"""Merit / ranking generation."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Application, ApplicationStatus, Evaluation, System


def compute_score(db: Session, application: Application) -> float:
    """Aggregate evaluation scores (normalized to a 0-100 scale, averaged)."""
    evals = db.scalars(
        select(Evaluation).where(Evaluation.application_id == application.id)
    ).all()
    if evals:
        normalized = [
            (e.score / e.max_score * 100.0) if e.max_score else 0.0 for e in evals
        ]
        return round(sum(normalized) / len(normalized), 4)
    # Fallback: a numeric merit-bearing form field if no formal evaluation exists.
    for fld in ("merit_score", "qualifying_marks", "cgpa", "technical_score"):
        val = application.data.get(fld)
        if isinstance(val, (int, float)):
            return float(val)
    return application.score or 0.0


def _tie_value(application: Application, key: str):
    field = key.rsplit("_", 1)[0]
    return application.data.get(field, "")


def generate_ranking(db: Session, system: System) -> list[Application]:
    """Score all applications for a system and assign dense merit ranks."""
    cfg = system.config or {}
    ranking_cfg = cfg.get("ranking", {})
    strategy = ranking_cfg.get("strategy", "score_desc")
    tie_breakers: list[str] = ranking_cfg.get("tie_breakers", [])

    # Only applications that have moved past the in-progress/early stages are
    # ranked. Applicants still filling in or awaiting eligibility are excluded.
    apps = db.scalars(
        select(Application).where(
            Application.system_id == system.id,
            Application.status.notin_(
                [ApplicationStatus.rejected, ApplicationStatus.withdrawn,
                 ApplicationStatus.ineligible, ApplicationStatus.draft,
                 ApplicationStatus.in_progress]
            ),
        )
    ).all()

    for app in apps:
        app.score = compute_score(db, app)

    reverse = strategy != "score_asc"

    def sort_key(a: Application):
        keys = [a.score or 0.0]
        for tb in tie_breakers:
            v = _tie_value(a, tb)
            # ascending tie-breaker => smaller is better; invert when overall reverse
            keys.append(v if not tb.endswith("_asc") else _negate(v))
        return tuple(keys)

    apps.sort(key=lambda a: (a.score or 0.0), reverse=reverse)
    # Apply tie-breakers within equal scores (stable secondary sort).
    if tie_breakers:
        apps.sort(key=lambda a: tuple(_tie_value(a, tb) for tb in tie_breakers))
        apps.sort(key=lambda a: (a.score or 0.0), reverse=reverse)

    for idx, app in enumerate(apps, start=1):
        app.rank = idx
        if app.status not in (ApplicationStatus.allocated, ApplicationStatus.enrolled):
            app.status = ApplicationStatus.ranked
    db.commit()
    return apps


def _negate(v):
    try:
        return -float(v)
    except (TypeError, ValueError):
        return v
