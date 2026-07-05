"""Analytics endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.core.deps import DbSession, require_viewer
from app.models import Campaign
from app.schemas.analytics import CampaignMetrics, OverviewMetrics, TimeseriesPoint
from app.services import analytics_service

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get("/overview", response_model=OverviewMetrics, dependencies=[Depends(require_viewer)])
def overview(db: DbSession):
    return analytics_service.overview(db)


@router.get("/campaigns/{campaign_id}", response_model=CampaignMetrics, dependencies=[Depends(require_viewer)])
def campaign_metrics(db: DbSession, campaign_id: int):
    campaign = db.get(Campaign, campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return analytics_service.campaign_metrics(db, campaign)


@router.get("/timeseries", response_model=list[TimeseriesPoint], dependencies=[Depends(require_viewer)])
def timeseries(db: DbSession, campaign_id: int | None = None, days: int = 30):
    return analytics_service.timeseries(db, campaign_id=campaign_id, days=days)
