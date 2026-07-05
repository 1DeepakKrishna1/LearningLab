"""Contact, custom field, and consent endpoints (incl. CSV bulk import)."""
from __future__ import annotations

import csv
import io

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy import String, func, or_, select

from app.core.audit import record_audit
from app.core.deps import CurrentUser, DbSession, require_marketer, require_viewer
from app.models import Consent, Contact, ContactCustomField
from app.models.enums import ConsentStatus
from app.schemas.common import Message, Page
from app.schemas.contact import (
    BulkImportResult,
    ConsentUpdate,
    ContactCreate,
    ContactOut,
    ContactUpdate,
    CustomFieldCreate,
    CustomFieldOut,
)

router = APIRouter(prefix="/contacts", tags=["Contacts"])

_STANDARD_COLS = {"email", "phone", "first_name", "last_name", "country", "timezone"}


@router.get("", response_model=Page[ContactOut], dependencies=[Depends(require_viewer)])
def list_contacts(
    db: DbSession,
    q: str | None = None,
    tag: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
):
    stmt = select(Contact)
    if q:
        like = f"%{q}%"
        stmt = stmt.where(or_(Contact.email.ilike(like), Contact.first_name.ilike(like),
                              Contact.last_name.ilike(like), Contact.phone.ilike(like)))
    if tag:
        stmt = stmt.where(func.coalesce(Contact.tags, "[]").cast(String).like(f'%"{tag}"%'))
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    items = list(db.scalars(stmt.order_by(Contact.id.desc())
                            .offset((page - 1) * page_size).limit(page_size)))
    return Page[ContactOut](items=items, total=total, page=page, page_size=page_size)


def _get_or_404(db, contact_id: int) -> Contact:
    contact = db.get(Contact, contact_id)
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    return contact


@router.post("", response_model=ContactOut, status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(require_marketer)])
def create_contact(db: DbSession, payload: ContactCreate, actor: CurrentUser):
    if payload.email and db.scalar(select(Contact).where(Contact.email == payload.email)):
        raise HTTPException(status_code=409, detail="Contact with this email already exists")
    contact = Contact(**payload.model_dump())
    db.add(contact)
    db.commit()
    db.refresh(contact)
    record_audit(db, action="contact.create", user=actor, entity_type="contact", entity_id=contact.id)
    return contact


@router.get("/{contact_id}", response_model=ContactOut, dependencies=[Depends(require_viewer)])
def get_contact(db: DbSession, contact_id: int):
    return _get_or_404(db, contact_id)


@router.patch("/{contact_id}", response_model=ContactOut, dependencies=[Depends(require_marketer)])
def update_contact(db: DbSession, contact_id: int, payload: ContactUpdate, actor: CurrentUser):
    contact = _get_or_404(db, contact_id)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(contact, key, value)
    db.commit()
    db.refresh(contact)
    record_audit(db, action="contact.update", user=actor, entity_type="contact", entity_id=contact.id)
    return contact


@router.delete("/{contact_id}", response_model=Message, dependencies=[Depends(require_marketer)])
def delete_contact(db: DbSession, contact_id: int, actor: CurrentUser):
    contact = _get_or_404(db, contact_id)
    db.delete(contact)
    db.commit()
    record_audit(db, action="contact.delete", user=actor, entity_type="contact", entity_id=contact_id)
    return Message(message="Contact deleted")


@router.post("/import", response_model=BulkImportResult, dependencies=[Depends(require_marketer)])
async def import_contacts_csv(db: DbSession, actor: CurrentUser, file: UploadFile = File(...)):
    """CSV bulk import. Standard columns are mapped; unknown columns become attributes."""
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Please upload a .csv file")
    raw = (await file.read()).decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(raw))
    received = created = updated = skipped = 0
    errors: list[str] = []

    for idx, row in enumerate(reader, start=2):
        received += 1
        email = (row.get("email") or "").strip().lower() or None
        phone = (row.get("phone") or "").strip() or None
        if not email and not phone:
            skipped += 1
            errors.append(f"row {idx}: no email or phone")
            continue
        existing = db.scalar(select(Contact).where(Contact.email == email)) if email else None
        attributes = {k: v for k, v in row.items() if k and k not in _STANDARD_COLS and k != "tags" and v}
        tags = [t.strip() for t in (row.get("tags") or "").split(";") if t.strip()]
        fields = {
            "email": email,
            "phone": phone,
            "first_name": (row.get("first_name") or "").strip() or None,
            "last_name": (row.get("last_name") or "").strip() or None,
            "country": (row.get("country") or "").strip() or None,
            "timezone": (row.get("timezone") or "UTC").strip() or "UTC",
        }
        if existing:
            for key, value in fields.items():
                if value:
                    setattr(existing, key, value)
            existing.attributes = {**(existing.attributes or {}), **attributes}
            if tags:
                existing.tags = sorted(set((existing.tags or []) + tags))
            updated += 1
        else:
            db.add(Contact(**fields, tags=tags, attributes=attributes))
            created += 1
    db.commit()
    record_audit(db, action="contact.import", user=actor,
                 detail={"received": received, "created": created, "updated": updated})
    return BulkImportResult(received=received, created=created, updated=updated, skipped=skipped, errors=errors[:50])


# --- Consent management ---
@router.put("/{contact_id}/consent", response_model=ContactOut, dependencies=[Depends(require_marketer)])
def update_consent(db: DbSession, contact_id: int, payload: ConsentUpdate, actor: CurrentUser):
    contact = _get_or_404(db, contact_id)
    consent = db.scalar(
        select(Consent).where(Consent.contact_id == contact_id, Consent.channel == payload.channel.value)
    )
    if not consent:
        consent = Consent(contact_id=contact_id, channel=payload.channel.value)
        db.add(consent)
    consent.status = payload.status.value
    consent.source = payload.source
    consent.updated_reason = payload.reason
    db.commit()
    db.refresh(contact)
    record_audit(db, action="consent.update", user=actor, entity_type="contact", entity_id=contact_id,
                 detail={"channel": payload.channel.value, "status": payload.status.value})
    return contact


# --- Custom fields ---
@router.get("/custom-fields/list", response_model=list[CustomFieldOut], dependencies=[Depends(require_viewer)])
def list_custom_fields(db: DbSession):
    return list(db.scalars(select(ContactCustomField).order_by(ContactCustomField.id)))


@router.post("/custom-fields", response_model=CustomFieldOut, status_code=201,
             dependencies=[Depends(require_marketer)])
def create_custom_field(db: DbSession, payload: CustomFieldCreate, actor: CurrentUser):
    if db.scalar(select(ContactCustomField).where(ContactCustomField.key == payload.key)):
        raise HTTPException(status_code=409, detail="Custom field key already exists")
    field = ContactCustomField(**payload.model_dump())
    db.add(field)
    db.commit()
    db.refresh(field)
    record_audit(db, action="custom_field.create", user=actor, entity_type="custom_field", entity_id=field.id)
    return field
