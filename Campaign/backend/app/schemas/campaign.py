"""Campaign schemas."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, model_validator

from app.models.enums import CampaignType, Channel
from app.schemas.common import ORMModel


class CampaignStepIn(BaseModel):
    step_order: int = 0
    channel: Channel
    template_id: int | None = None
    delay_hours: int = Field(default=0, ge=0)


class CampaignStepOut(ORMModel):
    id: int
    step_order: int
    channel: str
    template_id: int | None = None
    delay_hours: int


class CampaignBase(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str = ""
    type: CampaignType = CampaignType.ONE_TIME
    channel: Channel | None = None
    template_id: int | None = None
    segment_id: int | None = None
    scheduled_at: datetime | None = None
    timezone: str = "UTC"
    recurrence: dict[str, Any] | None = None
    steps: list[CampaignStepIn] = Field(default_factory=list)

    @model_validator(mode="after")
    def _validate(self) -> "CampaignBase":
        if self.type == CampaignType.MULTI_CHANNEL or self.type == CampaignType.DRIP:
            if not self.steps:
                raise ValueError(f"{self.type.value} campaigns require at least one step.")
        else:
            if not self.channel:
                raise ValueError("Single-channel campaigns require a 'channel'.")
        if self.type == CampaignType.RECURRING and not self.recurrence:
            raise ValueError("Recurring campaigns require a 'recurrence' definition.")
        return self


class CampaignCreate(CampaignBase):
    pass


class CampaignUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    channel: Channel | None = None
    template_id: int | None = None
    segment_id: int | None = None
    scheduled_at: datetime | None = None
    timezone: str | None = None
    recurrence: dict[str, Any] | None = None
    steps: list[CampaignStepIn] | None = None


class CampaignOut(ORMModel):
    id: int
    name: str
    description: str
    type: str
    status: str
    channel: str | None = None
    template_id: int | None = None
    segment_id: int | None = None
    scheduled_at: datetime | None = None
    timezone: str
    recurrence: dict[str, Any] | None = None
    next_run_at: datetime | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    approved_at: datetime | None = None
    rejection_reason: str | None = None
    created_by_id: int | None = None
    steps: list[CampaignStepOut] = []
    created_at: datetime
    updated_at: datetime


class ApprovalDecision(BaseModel):
    approved: bool
    reason: str | None = Field(default=None, max_length=500)


class ScheduleRequest(BaseModel):
    scheduled_at: datetime | None = Field(
        default=None, description="When to send. Omit/null for immediate send."
    )
