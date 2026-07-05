"""Segment endpoints with live preview of matching contacts."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select

from app.core.audit import record_audit
from app.core.deps import CurrentUser, DbSession, require_marketer, require_viewer
from app.models import Segment
from app.schemas.common import Message
from app.schemas.segment import (
    SegmentCreate,
    SegmentOut,
    SegmentPreview,
    SegmentUpdate,
)
from app.services import segment_engine

router = APIRouter(prefix="/segments", tags=["Segments"])


@router.get("", response_model=list[SegmentOut], dependencies=[Depends(require_viewer)])
def list_segments(db: DbSession):
    return list(db.scalars(select(Segment).order_by(Segment.updated_at.desc())))


def _get_or_404(db, segment_id: int) -> Segment:
    seg = db.get(Segment, segment_id)
    if not seg:
        raise HTTPException(status_code=404, detail="Segment not found")
    return seg


@router.post("", response_model=SegmentOut, status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(require_marketer)])
def create_segment(db: DbSession, payload: SegmentCreate, actor: CurrentUser):
    definition = payload.definition.model_dump()
    try:
        count = segment_engine.count(db, definition)
    except segment_engine.SegmentError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    seg = Segment(
        name=payload.name,
        description=payload.description,
        is_dynamic=payload.is_dynamic,
        definition=definition,
        cached_count=count,
        created_by_id=actor.id,
    )
    db.add(seg)
    db.commit()
    db.refresh(seg)
    record_audit(db, action="segment.create", user=actor, entity_type="segment", entity_id=seg.id)
    return seg


@router.get("/{segment_id}", response_model=SegmentOut, dependencies=[Depends(require_viewer)])
def get_segment(db: DbSession, segment_id: int):
    return _get_or_404(db, segment_id)


@router.patch("/{segment_id}", response_model=SegmentOut, dependencies=[Depends(require_marketer)])
def update_segment(db: DbSession, segment_id: int, payload: SegmentUpdate, actor: CurrentUser):
    seg = _get_or_404(db, segment_id)
    updates = payload.model_dump(exclude_unset=True)
    if "definition" in updates and updates["definition"] is not None:
        seg.definition = payload.definition.model_dump()
        seg.cached_count = segment_engine.count(db, seg.definition)
        updates.pop("definition")
    for key, value in updates.items():
        setattr(seg, key, value)
    db.commit()
    db.refresh(seg)
    record_audit(db, action="segment.update", user=actor, entity_type="segment", entity_id=seg.id)
    return seg


@router.delete("/{segment_id}", response_model=Message, dependencies=[Depends(require_marketer)])
def delete_segment(db: DbSession, segment_id: int, actor: CurrentUser):
    seg = _get_or_404(db, segment_id)
    db.delete(seg)
    db.commit()
    record_audit(db, action="segment.delete", user=actor, entity_type="segment", entity_id=segment_id)
    return Message(message="Segment deleted")


@router.get("/{segment_id}/preview", response_model=SegmentPreview, dependencies=[Depends(require_viewer)])
def preview_segment(db: DbSession, segment_id: int, limit: int = 10):
    seg = _get_or_404(db, segment_id)
    contacts = segment_engine.evaluate(db, seg.definition)
    sample = [
        {"id": c.id, "email": c.email, "first_name": c.first_name, "country": c.country}
        for c in contacts[:limit]
    ]
    return SegmentPreview(count=len(contacts), sample=sample)


@router.post("/preview", response_model=SegmentPreview, dependencies=[Depends(require_viewer)])
def preview_definition(db: DbSession, payload: SegmentCreate, limit: int = 10):
    """Preview an unsaved rule definition (used by the filter builder UI)."""
    try:
        contacts = segment_engine.evaluate(db, payload.definition.model_dump())
    except segment_engine.SegmentError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    sample = [{"id": c.id, "email": c.email, "first_name": c.first_name} for c in contacts[:limit]]
    return SegmentPreview(count=len(contacts), sample=sample)
