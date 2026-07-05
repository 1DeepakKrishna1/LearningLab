"""Template management endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select

from app.core.audit import record_audit
from app.core.deps import CurrentUser, DbSession, require_marketer, require_viewer
from app.models import Template, TemplateVersion
from app.models.enums import TemplateStatus
from app.schemas.common import Message, Page
from app.schemas.template import (
    TemplateCreate,
    TemplateOut,
    TemplatePreviewRequest,
    TemplatePreviewResponse,
    TemplateUpdate,
)
from app.services import template_service

router = APIRouter(prefix="/templates", tags=["Templates"])


@router.get("", response_model=Page[TemplateOut], dependencies=[Depends(require_viewer)])
def list_templates(
    db: DbSession,
    channel: str | None = None,
    category: str | None = None,
    status_filter: str | None = Query(default=None, alias="status"),
    q: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
):
    stmt = select(Template)
    if channel:
        stmt = stmt.where(Template.channel == channel)
    if category:
        stmt = stmt.where(Template.category == category)
    if status_filter:
        stmt = stmt.where(Template.status == status_filter)
    if q:
        stmt = stmt.where(Template.name.ilike(f"%{q}%"))
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    items = list(db.scalars(stmt.order_by(Template.updated_at.desc())
                            .offset((page - 1) * page_size).limit(page_size)))
    return Page[TemplateOut](items=items, total=total, page=page, page_size=page_size)


@router.post("", response_model=TemplateOut, status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(require_marketer)])
def create_template(db: DbSession, payload: TemplateCreate, actor: CurrentUser):
    data = payload.model_dump()
    data["channel"] = payload.channel.value
    if data.get("buttons"):
        data["buttons"] = [b for b in data["buttons"]]
    tpl = Template(**data, created_by_id=actor.id, status=TemplateStatus.DRAFT.value)
    db.add(tpl)
    db.commit()
    db.refresh(tpl)
    record_audit(db, action="template.create", user=actor, entity_type="template", entity_id=tpl.id)
    return tpl


def _get_or_404(db, template_id: int) -> Template:
    tpl = db.get(Template, template_id)
    if not tpl:
        raise HTTPException(status_code=404, detail="Template not found")
    return tpl


@router.get("/{template_id}", response_model=TemplateOut, dependencies=[Depends(require_viewer)])
def get_template(db: DbSession, template_id: int):
    return _get_or_404(db, template_id)


@router.patch("/{template_id}", response_model=TemplateOut, dependencies=[Depends(require_marketer)])
def update_template(db: DbSession, template_id: int, payload: TemplateUpdate, actor: CurrentUser):
    tpl = _get_or_404(db, template_id)
    # Snapshot current version before mutating (versioning).
    snapshot = {c.name: getattr(tpl, c.name) for c in tpl.__table__.columns}
    db.add(TemplateVersion(template_id=tpl.id, version=tpl.version, snapshot=_json_safe(snapshot)))

    updates = payload.model_dump(exclude_unset=True)
    if "status" in updates and updates["status"] is not None:
        updates["status"] = updates["status"].value if hasattr(updates["status"], "value") else updates["status"]
    for key, value in updates.items():
        setattr(tpl, key, value)
    tpl.version += 1
    db.commit()
    db.refresh(tpl)
    record_audit(db, action="template.update", user=actor, entity_type="template", entity_id=tpl.id)
    return tpl


@router.post("/{template_id}/clone", response_model=TemplateOut, dependencies=[Depends(require_marketer)])
def clone_template(db: DbSession, template_id: int, actor: CurrentUser):
    src = _get_or_404(db, template_id)
    cols = {c.name for c in src.__table__.columns} - {"id", "created_at", "updated_at"}
    data = {c: getattr(src, c) for c in cols}
    data["name"] = f"{src.name} (copy)"
    data["status"] = TemplateStatus.DRAFT.value
    data["version"] = 1
    clone = Template(**data)
    db.add(clone)
    db.commit()
    db.refresh(clone)
    record_audit(db, action="template.clone", user=actor, entity_type="template", entity_id=clone.id)
    return clone


@router.post("/{template_id}/preview", response_model=TemplatePreviewResponse,
             dependencies=[Depends(require_viewer)])
def preview_template(db: DbSession, template_id: int, payload: TemplatePreviewRequest):
    tpl = _get_or_404(db, template_id)
    return template_service.preview(tpl, payload.sample)


@router.post("/{template_id}/archive", response_model=TemplateOut, dependencies=[Depends(require_marketer)])
def archive_template(db: DbSession, template_id: int, actor: CurrentUser):
    tpl = _get_or_404(db, template_id)
    tpl.status = TemplateStatus.ARCHIVED.value
    db.commit()
    db.refresh(tpl)
    record_audit(db, action="template.archive", user=actor, entity_type="template", entity_id=tpl.id)
    return tpl


@router.delete("/{template_id}", response_model=Message, dependencies=[Depends(require_marketer)])
def delete_template(db: DbSession, template_id: int, actor: CurrentUser):
    tpl = _get_or_404(db, template_id)
    db.delete(tpl)
    db.commit()
    record_audit(db, action="template.delete", user=actor, entity_type="template", entity_id=template_id)
    return Message(message="Template deleted")


def _json_safe(snapshot: dict) -> dict:
    """Convert non-JSON values (datetimes) to strings for the version snapshot."""
    out = {}
    for key, value in snapshot.items():
        if hasattr(value, "isoformat"):
            out[key] = value.isoformat()
        else:
            out[key] = value
    return out
