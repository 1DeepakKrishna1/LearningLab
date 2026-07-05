"""Campaign endpoints: CRUD, lifecycle actions, approval, calendar, send."""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select

from app.core.audit import record_audit
from app.core.deps import CurrentUser, DbSession, require_marketer, require_viewer
from app.execution.engine import execute_campaign
from app.models import Campaign, CampaignStep
from app.models.enums import CampaignStatus as CS
from app.schemas.campaign import (
    ApprovalDecision,
    CampaignCreate,
    CampaignOut,
    CampaignUpdate,
    ScheduleRequest,
)
from app.schemas.common import Message, Page
from app.services import campaign_service as svc

router = APIRouter(prefix="/campaigns", tags=["Campaigns"])


def _get_or_404(db, campaign_id: int) -> Campaign:
    c = db.get(Campaign, campaign_id)
    if not c:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return c


def _apply_steps(db, campaign: Campaign, steps) -> None:
    campaign.steps.clear()
    db.flush()
    for s in steps:
        campaign.steps.append(
            CampaignStep(step_order=s.step_order, channel=s.channel.value,
                         template_id=s.template_id, delay_hours=s.delay_hours)
        )


@router.get("", response_model=Page[CampaignOut], dependencies=[Depends(require_viewer)])
def list_campaigns(
    db: DbSession,
    status_filter: str | None = Query(default=None, alias="status"),
    type_filter: str | None = Query(default=None, alias="type"),
    q: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
):
    stmt = select(Campaign)
    if status_filter:
        stmt = stmt.where(Campaign.status == status_filter)
    if type_filter:
        stmt = stmt.where(Campaign.type == type_filter)
    if q:
        stmt = stmt.where(Campaign.name.ilike(f"%{q}%"))
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    items = list(db.scalars(stmt.order_by(Campaign.updated_at.desc())
                            .offset((page - 1) * page_size).limit(page_size)))
    return Page[CampaignOut](items=items, total=total, page=page, page_size=page_size)


@router.get("/calendar", response_model=list[CampaignOut], dependencies=[Depends(require_viewer)])
def calendar(db: DbSession, start: datetime, end: datetime):
    """Campaigns scheduled within [start, end] for the calendar view."""
    stmt = select(Campaign).where(
        or_(
            Campaign.scheduled_at.between(start, end),
            Campaign.next_run_at.between(start, end),
        )
    )
    return list(db.scalars(stmt))


@router.post("", response_model=CampaignOut, status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(require_marketer)])
def create_campaign(db: DbSession, payload: CampaignCreate, actor: CurrentUser):
    campaign = Campaign(
        name=payload.name,
        description=payload.description,
        type=payload.type.value,
        channel=payload.channel.value if payload.channel else None,
        template_id=payload.template_id,
        segment_id=payload.segment_id,
        scheduled_at=payload.scheduled_at,
        timezone=payload.timezone,
        recurrence=payload.recurrence,
        status=CS.DRAFT.value,
        created_by_id=actor.id,
    )
    db.add(campaign)
    db.flush()
    _apply_steps(db, campaign, payload.steps)
    db.commit()
    db.refresh(campaign)
    record_audit(db, action="campaign.create", user=actor, entity_type="campaign", entity_id=campaign.id)
    return campaign


@router.get("/{campaign_id}", response_model=CampaignOut, dependencies=[Depends(require_viewer)])
def get_campaign(db: DbSession, campaign_id: int):
    return _get_or_404(db, campaign_id)


@router.patch("/{campaign_id}", response_model=CampaignOut, dependencies=[Depends(require_marketer)])
def update_campaign(db: DbSession, campaign_id: int, payload: CampaignUpdate, actor: CurrentUser):
    campaign = _get_or_404(db, campaign_id)
    svc.assert_editable(campaign.status)
    updates = payload.model_dump(exclude_unset=True)
    steps = updates.pop("steps", None)
    if "channel" in updates and updates["channel"] is not None:
        updates["channel"] = updates["channel"].value if hasattr(updates["channel"], "value") else updates["channel"]
    for key, value in updates.items():
        setattr(campaign, key, value)
    if steps is not None:
        _apply_steps(db, campaign, payload.steps)
    db.commit()
    db.refresh(campaign)
    record_audit(db, action="campaign.update", user=actor, entity_type="campaign", entity_id=campaign.id)
    return campaign


@router.post("/{campaign_id}/duplicate", response_model=CampaignOut, dependencies=[Depends(require_marketer)])
def duplicate_campaign(db: DbSession, campaign_id: int, actor: CurrentUser):
    src = _get_or_404(db, campaign_id)
    clone = Campaign(
        name=f"{src.name} (copy)", description=src.description, type=src.type,
        channel=src.channel, template_id=src.template_id, segment_id=src.segment_id,
        timezone=src.timezone, recurrence=src.recurrence, status=CS.DRAFT.value,
        created_by_id=actor.id,
    )
    db.add(clone)
    db.flush()
    for s in src.steps:
        clone.steps.append(CampaignStep(step_order=s.step_order, channel=s.channel,
                                        template_id=s.template_id, delay_hours=s.delay_hours))
    db.commit()
    db.refresh(clone)
    record_audit(db, action="campaign.duplicate", user=actor, entity_type="campaign", entity_id=clone.id)
    return clone


def _transition(db, campaign: Campaign, target: str, actor, **fields) -> Campaign:
    svc.assert_transition(campaign.status, target)
    campaign.status = target
    for key, value in fields.items():
        setattr(campaign, key, value)
    db.commit()
    db.refresh(campaign)
    record_audit(db, action=f"campaign.{target}", user=actor, entity_type="campaign", entity_id=campaign.id)
    return campaign


@router.post("/{campaign_id}/submit", response_model=CampaignOut, dependencies=[Depends(require_marketer)])
def submit_for_approval(db: DbSession, campaign_id: int, actor: CurrentUser):
    campaign = _get_or_404(db, campaign_id)
    return _transition(db, campaign, CS.PENDING_APPROVAL.value, actor)


@router.post("/{campaign_id}/approve", response_model=CampaignOut, dependencies=[Depends(require_marketer)])
def approve(db: DbSession, campaign_id: int, payload: ApprovalDecision, actor: CurrentUser):
    """Approve or reject. (Approval is a Marketer+/Admin action per RBAC.)"""
    campaign = _get_or_404(db, campaign_id)
    if payload.approved:
        return _transition(db, campaign, CS.APPROVED.value, actor,
                           approved_by_id=actor.id, approved_at=datetime.now(timezone.utc),
                           rejection_reason=None)
    return _transition(db, campaign, CS.DRAFT.value, actor, rejection_reason=payload.reason)


@router.post("/{campaign_id}/schedule", response_model=CampaignOut, dependencies=[Depends(require_marketer)])
def schedule(
    db: DbSession,
    campaign_id: int,
    payload: ScheduleRequest,
    actor: CurrentUser,
    background: BackgroundTasks,
):
    """Schedule a send. If ``scheduled_at`` is omitted -> immediate send."""
    campaign = _get_or_404(db, campaign_id)
    if campaign.status != CS.APPROVED.value:
        raise HTTPException(status_code=409, detail="Campaign must be approved before scheduling")

    if payload.scheduled_at is None:
        # Immediate send via background task.
        _transition(db, campaign, CS.SCHEDULED.value, actor, scheduled_at=datetime.now(timezone.utc))
        background.add_task(execute_campaign, campaign.id)
        return campaign
    return _transition(db, campaign, CS.SCHEDULED.value, actor,
                       scheduled_at=payload.scheduled_at, next_run_at=payload.scheduled_at)


@router.post("/{campaign_id}/pause", response_model=CampaignOut, dependencies=[Depends(require_marketer)])
def pause(db: DbSession, campaign_id: int, actor: CurrentUser):
    return _transition(db, _get_or_404(db, campaign_id), CS.PAUSED.value, actor)


@router.post("/{campaign_id}/resume", response_model=CampaignOut, dependencies=[Depends(require_marketer)])
def resume(db: DbSession, campaign_id: int, actor: CurrentUser, background: BackgroundTasks):
    campaign = _transition(db, _get_or_404(db, campaign_id), CS.SCHEDULED.value, actor)
    if campaign.scheduled_at and campaign.scheduled_at <= datetime.now(timezone.utc):
        background.add_task(execute_campaign, campaign.id)
    return campaign


@router.post("/{campaign_id}/cancel", response_model=CampaignOut, dependencies=[Depends(require_marketer)])
def cancel(db: DbSession, campaign_id: int, actor: CurrentUser):
    return _transition(db, _get_or_404(db, campaign_id), CS.CANCELLED.value, actor)


@router.post("/{campaign_id}/archive", response_model=CampaignOut, dependencies=[Depends(require_marketer)])
def archive(db: DbSession, campaign_id: int, actor: CurrentUser):
    return _transition(db, _get_or_404(db, campaign_id), CS.ARCHIVED.value, actor)


@router.delete("/{campaign_id}", response_model=Message, dependencies=[Depends(require_marketer)])
def delete_campaign(db: DbSession, campaign_id: int, actor: CurrentUser):
    campaign = _get_or_404(db, campaign_id)
    if campaign.status in {CS.SENDING.value}:
        raise HTTPException(status_code=409, detail="Cannot delete a campaign while it is sending")
    db.delete(campaign)
    db.commit()
    record_audit(db, action="campaign.delete", user=actor, entity_type="campaign", entity_id=campaign_id)
    return Message(message="Campaign deleted")
