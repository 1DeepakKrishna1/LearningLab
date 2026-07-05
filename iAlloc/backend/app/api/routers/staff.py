"""Operations for verifiers, evaluators and allocation authorities."""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.core.database import get_db
from app.models import (
    Application,
    ApplicationStatus,
    Document,
    DocStatus,
    Evaluation,
    StageStatus,
    System,
    User,
    UserRole,
)
from app.schemas.schemas import (
    ApplicationOut,
    DocumentOut,
    DocumentVerify,
    EvaluationCreate,
    EvaluationOut,
)
from app.services import allocation as allocation_svc
from app.services import ranking as ranking_svc
from app.services.workflow import audit, complete_stage

router = APIRouter(prefix="/api/systems/{system_id}/staff", tags=["staff"])

STAFF_ROLES = (
    UserRole.verifier, UserRole.evaluator, UserRole.allocation_authority,
    UserRole.payment_agency, UserRole.auditor, UserRole.support,
    UserRole.institution, UserRole.reporting_authority,
    UserRole.system_admin, UserRole.product_admin,
)


def _system_guard(system_id: int, user: User, db: Session) -> System:
    system = db.get(System, system_id)
    if not system:
        raise HTTPException(status_code=404, detail="System not found")
    if user.role != UserRole.product_admin and user.system_id != system.id:
        raise HTTPException(status_code=403, detail="Not your system")
    return system


@router.get("/applications", response_model=list[ApplicationOut])
def list_applications(
    system_id: int,
    status: ApplicationStatus | None = Query(default=None),
    user: User = Depends(require_roles(*STAFF_ROLES)),
    db: Session = Depends(get_db),
):
    system = _system_guard(system_id, user, db)
    stmt = select(Application).where(Application.system_id == system.id)
    if status:
        stmt = stmt.where(Application.status == status)
    return db.scalars(stmt.order_by(Application.rank.is_(None), Application.rank)).all()


# ----------------------------- Verifier ----------------------------- #
@router.get("/documents/pending", response_model=list[DocumentOut])
def pending_documents(
    system_id: int,
    user: User = Depends(require_roles(UserRole.verifier, UserRole.system_admin,
                                      UserRole.product_admin)),
    db: Session = Depends(get_db),
):
    system = _system_guard(system_id, user, db)
    return db.scalars(
        select(Document)
        .join(Application, Document.application_id == Application.id)
        .where(Application.system_id == system.id, Document.status == DocStatus.pending)
    ).all()


@router.patch("/documents/{doc_id}/verify", response_model=DocumentOut)
def verify_document(
    system_id: int, doc_id: int, body: DocumentVerify,
    user: User = Depends(require_roles(UserRole.verifier, UserRole.system_admin,
                                      UserRole.product_admin)),
    db: Session = Depends(get_db),
):
    system = _system_guard(system_id, user, db)
    doc = db.get(Document, doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    doc.status = body.status
    doc.remarks = body.remarks
    doc.verified_by = user.id
    audit(db, system_id=system.id, actor_id=user.id, action="document_verified",
          entity_type="document", entity_id=doc.id,
          detail={"status": body.status.value})
    db.commit()
    db.refresh(doc)
    return doc


@router.post("/applications/{app_id}/eligibility", response_model=ApplicationOut)
def set_eligibility(
    system_id: int, app_id: int, eligible: bool, remarks: str = "",
    user: User = Depends(require_roles(UserRole.verifier, UserRole.system_admin,
                                      UserRole.product_admin)),
    db: Session = Depends(get_db),
):
    system = _system_guard(system_id, user, db)
    app = db.get(Application, app_id)
    if not app or app.system_id != system.id:
        raise HTTPException(status_code=404, detail="Application not found")
    app.status = ApplicationStatus.eligible if eligible else ApplicationStatus.ineligible
    # Complete the eligibility stage if present.
    complete_stage(db, app, system, "eligibility", actor_id=user.id,
                   data={"eligible": eligible}, remarks=remarks)
    db.commit()
    db.refresh(app)
    return app


# ----------------------------- Evaluator ----------------------------- #
@router.post("/evaluations", response_model=EvaluationOut, status_code=201)
def create_evaluation(
    system_id: int, body: EvaluationCreate,
    user: User = Depends(require_roles(UserRole.evaluator, UserRole.system_admin,
                                      UserRole.product_admin)),
    db: Session = Depends(get_db),
):
    system = _system_guard(system_id, user, db)
    app = db.get(Application, body.application_id)
    if not app or app.system_id != system.id:
        raise HTTPException(status_code=404, detail="Application not found")
    ev = Evaluation(
        application_id=app.id, stage_key=body.stage_key, evaluator_id=user.id,
        score=body.score, max_score=body.max_score, criteria=body.criteria,
        remarks=body.remarks,
    )
    db.add(ev)
    app.status = ApplicationStatus.evaluated
    audit(db, system_id=system.id, actor_id=user.id, action="evaluation_recorded",
          entity_type="application", entity_id=app.id,
          detail={"score": body.score, "max": body.max_score})
    db.commit()
    db.refresh(ev)
    return ev


@router.get("/evaluations/{app_id}", response_model=list[EvaluationOut])
def list_evaluations(
    system_id: int, app_id: int,
    user: User = Depends(require_roles(*STAFF_ROLES)), db: Session = Depends(get_db),
):
    _system_guard(system_id, user, db)
    return db.scalars(
        select(Evaluation).where(Evaluation.application_id == app_id)
    ).all()


# ----------------------------- Allocation authority ----------------------------- #
@router.post("/ranking/generate", response_model=list[ApplicationOut])
def generate_ranking(
    system_id: int,
    user: User = Depends(require_roles(UserRole.allocation_authority,
                                      UserRole.reporting_authority,
                                      UserRole.system_admin, UserRole.product_admin)),
    db: Session = Depends(get_db),
):
    system = _system_guard(system_id, user, db)
    ranked = ranking_svc.generate_ranking(db, system)
    audit(db, system_id=system.id, actor_id=user.id, action="ranking_generated",
          detail={"count": len(ranked)})
    db.commit()
    return ranked


@router.post("/allocation/run")
def run_allocation(
    system_id: int, round_no: int = 1,
    user: User = Depends(require_roles(UserRole.allocation_authority,
                                      UserRole.system_admin, UserRole.product_admin)),
    db: Session = Depends(get_db),
):
    system = _system_guard(system_id, user, db)
    result = allocation_svc.run_allocation(db, system, actor_id=user.id, round_no=round_no)
    audit(db, system_id=system.id, actor_id=user.id, action="allocation_run",
          detail=result)
    db.commit()
    return result


@router.get("/merit-list", response_model=list[ApplicationOut])
def merit_list(
    system_id: int,
    user: User = Depends(require_roles(*STAFF_ROLES)), db: Session = Depends(get_db),
):
    system = _system_guard(system_id, user, db)
    return db.scalars(
        select(Application)
        .where(Application.system_id == system.id, Application.rank.isnot(None))
        .order_by(Application.rank)
    ).all()
