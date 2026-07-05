"""Analytics and reporting schemas."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from app.models.enums import ReportFormat, ReportSchedule
from app.schemas.common import ORMModel


class CampaignMetrics(BaseModel):
    campaign_id: int
    campaign_name: str
    channel: str | None = None
    sent: int = 0
    delivered: int = 0
    opened: int = 0
    clicked: int = 0
    bounced: int = 0
    failed: int = 0
    unsubscribed: int = 0
    converted: int = 0
    replied: int = 0
    # rates (0..1)
    delivery_rate: float = 0.0
    open_rate: float = 0.0
    click_rate: float = 0.0
    bounce_rate: float = 0.0
    failure_rate: float = 0.0
    reply_rate: float = 0.0
    conversion_rate: float = 0.0


class OverviewMetrics(BaseModel):
    total_campaigns: int = 0
    active_campaigns: int = 0
    total_contacts: int = 0
    sent: int = 0
    delivered: int = 0
    opened: int = 0
    clicked: int = 0
    by_channel: dict[str, CampaignMetrics] = {}


class TimeseriesPoint(BaseModel):
    date: str
    sent: int = 0
    delivered: int = 0
    opened: int = 0
    clicked: int = 0


class ReportCreate(BaseModel):
    name: str
    report_type: str = "campaign_performance"
    fmt: ReportFormat = ReportFormat.CSV
    schedule: ReportSchedule = ReportSchedule.NONE
    filters: dict | None = None


class ReportOut(ORMModel):
    id: int
    name: str
    report_type: str
    fmt: str
    schedule: str
    last_generated_at: datetime | None = None
    file_path: str | None = None
    created_at: datetime
