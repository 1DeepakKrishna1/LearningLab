from __future__ import annotations

import secrets

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models import (
    Allocation,
    AllocationOption,
    Application,
    ApplicationStatus,
    Document,
    DocStatus,
    Payment,
    PaymentStatus,
    Preference,
    StageStatus,
    System,
    User,
    UserRole,
)
from app.schemas.schemas import (
    AllocationDecision,
    AllocationOut,
    ApplicationCreate,
    ApplicationDetail,
    ApplicationOut,
    ApplicationUpdate,
    DocumentCreate,
    DocumentOut,
    PaymentCreate,
    PaymentOut,
    PreferenceOut,
    PreferenceSet,
    StageActionRequest,
    StageProgress,
)
from app.services.config_builder import stage_by_key
from app.services.workflow import (
    audit,
    complete_stage,
    init_stage_records,
    progress_summary,
)

router = APIRouter(prefix="/api/applications", tags=["applications"])


def _load_owned(db: Session, app_id: int, user: User) -> Application:
    app = db.get(Application, app_id)
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")
    if user.role == UserRole.applicant and app.applicant_id != user.id:
        raise HTTPException(status_code=403, detail="Not your application")
    if user.role not in (UserRole.product_admin,) and user.system_id != app.system_id:
        raise HTTPException(status_code=403, detail="Different system")
    return app


def _detail(db: Session, app: Application, system: System) -> ApplicationDetail:
    out = ApplicationDetail.model_validate(app)
    out.progress = [StageProgress(**p) for p in progress_summary(app, system)]
    out.applicant_name = app.applicant.full_name if app.applicant else None
    return out


@router.post("", response_model=ApplicationDetail, status_code=201)
def create_application(
    body: ApplicationCreate, user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if user.role != UserRole.applicant or not user.system_id:
        raise HTTPException(status_code=403, detail="Only applicants may apply")
    system = db.get(System, user.system_id)
    app = Application(
        system_id=system.id,
        applicant_id=user.id,
        reference_no=f"{system.key.upper()}-{secrets.token_hex(3).upper()}",
        data=body.data,
        status=ApplicationStatus.in_progress,
    )
    db.add(app)
    db.flush()
    init_stage_records(db, app, system)
    audit(db, system_id=system.id, actor_id=user.id, action="application_created",
          entity_type="application", entity_id=app.id)
    db.commit()
    db.refresh(app)
    return _detail(db, app, system)


@router.get("/mine", response_model=list[ApplicationOut])
def my_applications(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return db.scalars(
        select(Application).where(Application.applicant_id == user.id)
    ).all()


@router.get("/{app_id}", response_model=ApplicationDetail)
def get_application(app_id: int, user: User = Depends(get_current_user),
                    db: Session = Depends(get_db)):
    app = _load_owned(db, app_id, user)
    return _detail(db, app, db.get(System, app.system_id))


@router.patch("/{app_id}", response_model=ApplicationDetail)
def update_application(app_id: int, body: ApplicationUpdate,
                       user: User = Depends(get_current_user),
                       db: Session = Depends(get_db)):
    app = _load_owned(db, app_id, user)
    app.data = {**(app.data or {}), **body.data}
    db.commit()
    db.refresh(app)
    return _detail(db, app, db.get(System, app.system_id))


@router.post("/{app_id}/stages/action", response_model=ApplicationDetail)
def stage_action(app_id: int, body: StageActionRequest,
                 user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Generic stage transition (e.g. applicant submits registration / confirms a step)."""
    app = _load_owned(db, app_id, user)
    system = db.get(System, app.system_id)
    stage = stage_by_key(system.config or {}, body.stage_key)
    if not stage:
        raise HTTPException(status_code=404, detail="Stage not found")
    if body.status == StageStatus.completed:
        complete_stage(db, app, system, body.stage_key, actor_id=user.id,
                       data=body.data, remarks=body.remarks)
    db.commit()
    db.refresh(app)
    return _detail(db, app, system)


# ----------------------------- Documents ----------------------------- #
@router.post("/{app_id}/documents", response_model=DocumentOut, status_code=201)
def upload_document(app_id: int, body: DocumentCreate,
                    user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    app = _load_owned(db, app_id, user)
    doc = Document(
        application_id=app.id, name=body.name, doc_type=body.doc_type,
        content_text=body.content_text, file_ref=body.file_ref,
    )
    db.add(doc)
    audit(db, system_id=app.system_id, actor_id=user.id, action="document_uploaded",
          entity_type="document", entity_id=app.id, detail={"name": body.name})
    db.commit()
    db.refresh(doc)
    return doc


@router.get("/{app_id}/documents", response_model=list[DocumentOut])
def list_documents(app_id: int, user: User = Depends(get_current_user),
                   db: Session = Depends(get_db)):
    app = _load_owned(db, app_id, user)
    return db.scalars(select(Document).where(Document.application_id == app.id)).all()


# ----------------------------- Preferences ----------------------------- #
@router.put("/{app_id}/preferences", response_model=list[PreferenceOut])
def set_preferences(app_id: int, body: PreferenceSet,
                    user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    app = _load_owned(db, app_id, user)
    db.execute(Preference.__table__.delete().where(Preference.application_id == app.id))
    for item in body.preferences:
        db.add(
            Preference(
                application_id=app.id, option_key=item.option_key,
                option_label=item.option_label, priority=item.priority,
            )
        )
    db.commit()
    return db.scalars(
        select(Preference).where(Preference.application_id == app.id)
        .order_by(Preference.priority)
    ).all()


@router.get("/{app_id}/preferences", response_model=list[PreferenceOut])
def get_preferences(app_id: int, user: User = Depends(get_current_user),
                    db: Session = Depends(get_db)):
    app = _load_owned(db, app_id, user)
    return db.scalars(
        select(Preference).where(Preference.application_id == app.id)
        .order_by(Preference.priority)
    ).all()


# ----------------------------- Payments ----------------------------- #
@router.post("/{app_id}/payments", response_model=PaymentOut, status_code=201)
def make_payment(app_id: int, body: PaymentCreate,
                 user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Simulated payment gateway: marks the payment as paid immediately."""
    app = _load_owned(db, app_id, user)
    pay = Payment(
        application_id=app.id, amount=body.amount, currency=body.currency,
        purpose=body.purpose, status=PaymentStatus.paid,
        reference=f"PAY-{secrets.token_hex(4).upper()}",
    )
    db.add(pay)
    audit(db, system_id=app.system_id, actor_id=user.id, action="payment_made",
          entity_type="payment", entity_id=app.id, detail={"amount": body.amount})
    db.commit()
    db.refresh(pay)
    return pay


@router.get("/{app_id}/payments", response_model=list[PaymentOut])
def list_payments(app_id: int, user: User = Depends(get_current_user),
                  db: Session = Depends(get_db)):
    app = _load_owned(db, app_id, user)
    return db.scalars(select(Payment).where(Payment.application_id == app.id)).all()


# ----------------------------- Allocation view / response ----------------------------- #
@router.get("/{app_id}/allocation", response_model=list[AllocationOut])
def my_allocation(app_id: int, user: User = Depends(get_current_user),
                  db: Session = Depends(get_db)):
    app = _load_owned(db, app_id, user)
    return db.scalars(select(Allocation).where(Allocation.application_id == app.id)).all()


@router.post("/{app_id}/allocation/respond", response_model=AllocationOut)
def respond_allocation(app_id: int, body: AllocationDecision,
                       user: User = Depends(get_current_user),
                       db: Session = Depends(get_db)):
    app = _load_owned(db, app_id, user)
    alloc = db.scalar(
        select(Allocation).where(Allocation.application_id == app.id)
        .order_by(Allocation.round.desc())
    )
    if not alloc:
        raise HTTPException(status_code=404, detail="No allocation to respond to")
    if body.decision not in ("accepted", "declined"):
        raise HTTPException(status_code=400, detail="decision must be accepted/declined")
    alloc.status = body.decision
    if body.decision == "accepted":
        app.status = ApplicationStatus.enrolled
    audit(db, system_id=app.system_id, actor_id=user.id,
          action=f"allocation_{body.decision}", entity_type="allocation",
          entity_id=alloc.id)
    db.commit()
    db.refresh(alloc)
    return alloc
