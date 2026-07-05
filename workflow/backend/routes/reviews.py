"""Review / publish workflow for Tools, Agents, and Templates."""
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Optional

from models import ReviewItem, ReviewCreate, ReviewDecision, AuditLog
from db import reviews_db, tools_db, agents_db, workflows_db, library_workflow_ids, audit_logs
from routes.auth import get_current_user, require_admin
from persistence import save_user_workflows

router = APIRouter()


def _log(actor, action, resource_id, resource_name, details=None):
    audit_logs.append(AuditLog(
        user_id=actor.id, user_email=actor.email, user_name=actor.name,
        action=action, resource_type="review",
        resource_id=resource_id, resource_name=resource_name,
        details=details or {},
    ))


@router.get("/", response_model=List[ReviewItem])
def list_reviews(
    status: Optional[str] = Query(None),
    type: Optional[str] = Query(None),
    actor=Depends(get_current_user),
):
    items = list(reviews_db.values())
    if status:
        items = [r for r in items if r.status == status]
    if type:
        items = [r for r in items if r.type == type]
    items.sort(key=lambda r: r.submitted_at, reverse=True)
    return items


@router.post("/", response_model=ReviewItem)
def submit_review(payload: ReviewCreate, actor=Depends(require_admin)):
    review = ReviewItem(
        type=payload.type,
        item_id=payload.item_id,
        item_name=payload.item_name,
        item_data=payload.item_data,
        submitted_by_id=actor.id,
        submitted_by_name=actor.name,
        status="pending",
    )
    reviews_db[review.id] = review
    _log(actor, "create", review.id, f"Review: {payload.item_name}")
    return review


@router.put("/{review_id}/approve", response_model=ReviewItem)
def approve(review_id: str, payload: ReviewDecision, actor=Depends(require_admin)):
    r = reviews_db.get(review_id)
    if not r:
        raise HTTPException(status_code=404, detail="Review not found")
    r.status = "approved"
    r.reviewed_by_id = actor.id
    r.reviewed_by_name = actor.name
    r.reviewed_at = datetime.utcnow()
    r.notes = payload.notes

    # Apply the approval to the underlying item
    if r.type == "tool" and r.item_id in tools_db:
        tools_db[r.item_id].review_status = "approved"
    elif r.type == "agent" and r.item_id in agents_db:
        agents_db[r.item_id].review_status = "approved"
    elif r.type == "template" and r.item_id in workflows_db:
        workflows_db[r.item_id].review_status = "approved" if hasattr(workflows_db[r.item_id], "review_status") else None

    _log(actor, "approve", r.id, r.item_name, details={"notes": payload.notes})
    return r


@router.put("/{review_id}/reject", response_model=ReviewItem)
def reject(review_id: str, payload: ReviewDecision, actor=Depends(require_admin)):
    r = reviews_db.get(review_id)
    if not r:
        raise HTTPException(status_code=404, detail="Review not found")
    r.status = "rejected"
    r.reviewed_by_id = actor.id
    r.reviewed_by_name = actor.name
    r.reviewed_at = datetime.utcnow()
    r.notes = payload.notes

    if r.type == "tool" and r.item_id in tools_db:
        tools_db[r.item_id].review_status = "rejected"
    elif r.type == "agent" and r.item_id in agents_db:
        agents_db[r.item_id].review_status = "rejected"

    _log(actor, "reject", r.id, r.item_name, details={"notes": payload.notes})
    return r


@router.delete("/{review_id}")
def delete_review(review_id: str, actor=Depends(require_admin)):
    r = reviews_db.pop(review_id, None)
    if not r:
        raise HTTPException(status_code=404, detail="Review not found")
    return {"message": "deleted"}
