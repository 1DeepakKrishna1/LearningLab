"""Provider configuration endpoints with health checks."""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select

from app.core.audit import record_audit
from app.core.deps import CurrentUser, DbSession, require_admin, require_viewer
from app.models import ProviderConfig
from app.providers import get_provider_factory
from app.schemas.common import Message
from app.schemas.provider import (
    HealthCheckResult,
    ProviderConfigCreate,
    ProviderConfigOut,
    ProviderConfigUpdate,
)

router = APIRouter(prefix="/providers", tags=["Providers"])


def _get_or_404(db, provider_id: int) -> ProviderConfig:
    pc = db.get(ProviderConfig, provider_id)
    if not pc:
        raise HTTPException(status_code=404, detail="Provider config not found")
    return pc


def _clear_other_defaults(db, channel: str, keep_id: int | None) -> None:
    for pc in db.scalars(select(ProviderConfig).where(ProviderConfig.channel == channel,
                                                       ProviderConfig.is_default.is_(True))):
        if pc.id != keep_id:
            pc.is_default = False


@router.get("", response_model=list[ProviderConfigOut], dependencies=[Depends(require_viewer)])
def list_providers(db: DbSession):
    return list(db.scalars(select(ProviderConfig).order_by(ProviderConfig.channel, ProviderConfig.id)))


@router.post("", response_model=ProviderConfigOut, status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(require_admin)])
def create_provider(db: DbSession, payload: ProviderConfigCreate, actor: CurrentUser):
    pc = ProviderConfig(
        name=payload.name, channel=payload.channel.value, provider_type=payload.provider_type.value,
        config=payload.config, mode=payload.mode, is_default=payload.is_default, is_active=payload.is_active,
    )
    db.add(pc)
    db.flush()
    if pc.is_default:
        _clear_other_defaults(db, pc.channel, pc.id)
    db.commit()
    db.refresh(pc)
    record_audit(db, action="provider.create", user=actor, entity_type="provider", entity_id=pc.id)
    return pc


@router.patch("/{provider_id}", response_model=ProviderConfigOut, dependencies=[Depends(require_admin)])
def update_provider(db: DbSession, provider_id: int, payload: ProviderConfigUpdate, actor: CurrentUser):
    pc = _get_or_404(db, provider_id)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(pc, key, value)
    if pc.is_default:
        _clear_other_defaults(db, pc.channel, pc.id)
    db.commit()
    db.refresh(pc)
    record_audit(db, action="provider.update", user=actor, entity_type="provider", entity_id=pc.id)
    return pc


@router.delete("/{provider_id}", response_model=Message, dependencies=[Depends(require_admin)])
def delete_provider(db: DbSession, provider_id: int, actor: CurrentUser):
    pc = _get_or_404(db, provider_id)
    db.delete(pc)
    db.commit()
    record_audit(db, action="provider.delete", user=actor, entity_type="provider", entity_id=provider_id)
    return Message(message="Provider config deleted")


@router.post("/{provider_id}/health", response_model=HealthCheckResult, dependencies=[Depends(require_viewer)])
async def health_check(db: DbSession, provider_id: int):
    pc = _get_or_404(db, provider_id)
    factory = get_provider_factory(db)
    healthy, detail = await factory.health_check(pc)
    pc.last_health_status = "healthy" if healthy else "unhealthy"
    pc.last_health_checked_at = datetime.now(timezone.utc)
    db.commit()
    return HealthCheckResult(healthy=healthy, status=pc.last_health_status, detail=detail)
