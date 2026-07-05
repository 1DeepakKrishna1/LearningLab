"""Template schemas with channel-aware validation."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, model_validator

from app.models.enums import Channel, TemplateStatus
from app.schemas.common import ORMModel


class TemplateButton(BaseModel):
    label: str = Field(max_length=40)
    action: str = Field(max_length=500)


class TemplateBase(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    channel: Channel
    category: str = "general"
    # Email
    subject: str | None = Field(default=None, max_length=500)
    preheader: str | None = Field(default=None, max_length=500)
    html_content: str | None = None
    # SMS
    text_content: str | None = None
    # Push
    title: str | None = Field(default=None, max_length=255)
    body: str | None = None
    image_url: str | None = Field(default=None, max_length=1000)
    deep_link: str | None = Field(default=None, max_length=1000)
    buttons: list[TemplateButton] | None = None
    variables: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _validate_channel_fields(self) -> "TemplateBase":
        if self.channel == Channel.EMAIL and not (self.subject and self.html_content):
            raise ValueError("Email templates require 'subject' and 'html_content'.")
        if self.channel == Channel.SMS and not self.text_content:
            raise ValueError("SMS templates require 'text_content'.")
        if self.channel == Channel.PUSH and not (self.title and self.body):
            raise ValueError("Push templates require 'title' and 'body'.")
        return self


class TemplateCreate(TemplateBase):
    pass


class TemplateUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=255)
    category: str | None = None
    status: TemplateStatus | None = None
    subject: str | None = None
    preheader: str | None = None
    html_content: str | None = None
    text_content: str | None = None
    title: str | None = None
    body: str | None = None
    image_url: str | None = None
    deep_link: str | None = None
    buttons: list[TemplateButton] | None = None
    variables: list[str] | None = None


class TemplateOut(ORMModel):
    id: int
    name: str
    channel: str
    category: str
    status: str
    version: int
    subject: str | None = None
    preheader: str | None = None
    html_content: str | None = None
    text_content: str | None = None
    title: str | None = None
    body: str | None = None
    image_url: str | None = None
    deep_link: str | None = None
    buttons: list[dict[str, Any]] | None = None
    variables: list[str] = []
    created_at: datetime
    updated_at: datetime


class TemplatePreviewRequest(BaseModel):
    sample: dict[str, Any] = Field(default_factory=dict, description="Variable values for rendering.")


class TemplatePreviewResponse(BaseModel):
    subject: str | None = None
    body: str
    sms_segments: int | None = None
    char_count: int | None = None
