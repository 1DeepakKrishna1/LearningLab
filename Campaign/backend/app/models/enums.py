"""Enumerations shared across models and schemas."""
from __future__ import annotations

import enum


class RoleName(str, enum.Enum):
    ADMIN = "admin"
    MARKETER = "marketer"
    VIEWER = "viewer"


class Channel(str, enum.Enum):
    EMAIL = "email"
    SMS = "sms"
    PUSH = "push"


class CampaignType(str, enum.Enum):
    ONE_TIME = "one_time"
    RECURRING = "recurring"
    DRIP = "drip"
    MULTI_CHANNEL = "multi_channel"


class CampaignStatus(str, enum.Enum):
    DRAFT = "draft"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    SCHEDULED = "scheduled"
    SENDING = "sending"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"
    CANCELLED = "cancelled"
    ARCHIVED = "archived"


class DeliveryStatus(str, enum.Enum):
    PENDING = "pending"
    QUEUED = "queued"
    SENT = "sent"
    DELIVERED = "delivered"
    FAILED = "failed"
    BOUNCED = "bounced"
    SKIPPED = "skipped"  # e.g. suppressed by consent


class EventType(str, enum.Enum):
    # Email
    SENT = "sent"
    DELIVERED = "delivered"
    OPENED = "opened"
    CLICKED = "clicked"
    BOUNCED = "bounced"
    COMPLAINED = "complained"
    UNSUBSCRIBED = "unsubscribed"
    # SMS
    FAILED = "failed"
    REPLIED = "replied"
    # Push
    ACTION_CLICKED = "action_clicked"
    CONVERTED = "converted"


class TemplateStatus(str, enum.Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    ARCHIVED = "archived"


class ConsentStatus(str, enum.Enum):
    SUBSCRIBED = "subscribed"
    UNSUBSCRIBED = "unsubscribed"
    PENDING = "pending"


class ProviderType(str, enum.Enum):
    SMTP = "smtp"
    SENDGRID = "sendgrid"
    TWILIO = "twilio"
    FCM = "fcm"
    ONESIGNAL = "onesignal"
    CONSOLE = "console"


class ReportFormat(str, enum.Enum):
    CSV = "csv"
    EXCEL = "excel"
    PDF = "pdf"


class ReportSchedule(str, enum.Enum):
    NONE = "none"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
