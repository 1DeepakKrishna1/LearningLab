from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.core.database import get_db
from app.models import (
    AIInvocation,
    AllocationOption,
    Application,
    Document,
    Evaluation,
    Preference,
    System,
    User,
    UserRole,
)
from app.schemas.schemas import AIRequest, AIResponse
from app.services.ai import AIError, is_configured, run_stage_ai

router = APIRouter(prefix="/api/ai", tags=["ai"])


@router.get("/status")
def ai_status():
    return {"configured": is_configured()}


def _build_context(db: Session, app: Application, stage_type: str) -> dict:
    """Assemble stage-relevant context for the model from live application data."""
    ctx: dict = {"reference_no": app.reference_no, "application_data": app.data}
    if stage_type in ("document", "verification", "eligibility"):
        docs = db.scalars(select(Document).where(Document.application_id == app.id)).all()
        ctx["documents"] = [
            {"name": d.name, "type": d.doc_type, "status": d.status.value,
             "text": (d.content_text or "")[:1500]}
            for d in docs
        ]
    if stage_type in ("evaluation", "ranking"):
        evals = db.scalars(
            select(Evaluation).where(Evaluation.application_id == app.id)
        ).all()
        ctx["evaluations"] = [
            {"score": e.score, "max": e.max_score, "criteria": e.criteria} for e in evals
        ]
        ctx["score"] = app.score
        ctx["rank"] = app.rank
    if stage_type in ("preference", "allocation"):
        opts = db.scalars(
            select(AllocationOption).where(AllocationOption.system_id == app.system_id)
        ).all()
        ctx["available_options"] = [
            {"key": o.key, "label": o.label,
             "remaining": max(o.capacity - o.filled, 0)}
            for o in opts
        ]
        prefs = db.scalars(
            select(Preference).where(Preference.application_id == app.id)
            .order_by(Preference.priority)
        ).all()
        ctx["preferences"] = [{"priority": p.priority, "option": p.option_label or p.option_key} for p in prefs]
        ctx["rank"] = app.rank
    return ctx


@router.post("/assist", response_model=AIResponse)
def assist(body: AIRequest, user: User = Depends(get_current_user),
           db: Session = Depends(get_db)):
    system = db.get(System, body.system_id)
    if not system:
        raise HTTPException(status_code=404, detail="System not found")
    if user.role != UserRole.product_admin and user.system_id != system.id:
        raise HTTPException(status_code=403, detail="Not your system")

    from app.services.config_builder import stage_by_key

    stage = stage_by_key(system.config or {}, body.stage_key)
    if not stage:
        raise HTTPException(status_code=404, detail="Stage not found")

    context: dict = {}
    if body.application_id:
        app = db.get(Application, body.application_id)
        if app and app.system_id == system.id:
            context = _build_context(db, app, stage.get("type", ""))

    try:
        result = run_stage_ai(
            db, system=system, stage_key=body.stage_key, user_id=user.id,
            user_input=body.user_input or f"Assist with the {stage['name']} stage.",
            context=context, override_task=body.task,
        )
    except AIError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return AIResponse(**result)


@router.get("/invocations/{system_id}")
def invocations(
    system_id: int,
    user: User = Depends(require_roles(UserRole.system_admin, UserRole.auditor,
                                      UserRole.product_admin, UserRole.reporting_authority)),
    db: Session = Depends(get_db),
):
    if user.role != UserRole.product_admin and user.system_id != system_id:
        raise HTTPException(status_code=403, detail="Not your system")
    rows = db.scalars(
        select(AIInvocation).where(AIInvocation.system_id == system_id)
        .order_by(AIInvocation.created_at.desc()).limit(100)
    ).all()
    return [
        {"id": r.id, "stage_key": r.stage_key, "task": r.task, "model": r.model,
         "tokens": r.tokens, "created_at": r.created_at,
         "prompt": r.prompt[:500], "response": r.response[:2000]}
        for r in rows
    ]
