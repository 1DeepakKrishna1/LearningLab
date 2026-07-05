"""ORM model definitions for the Campaign Management Platform.

Tables (per spec): users, roles, permissions, user_roles, role_permissions,
refresh_tokens, campaigns, campaign_steps, templates, contacts,
contact_custom_fields, segments, segment_rules, deliveries, provider_configs,
event_logs, analytics_snapshots, reports, audit_logs, consents.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Table,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=utcnow, onupdate=utcnow, nullable=False
    )


# --------------------------------------------------------------------------- #
# Auth & RBAC
# --------------------------------------------------------------------------- #
user_roles = Table(
    "user_roles",
    Base.metadata,
    Column("user_id", ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    Column("role_id", ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
)

role_permissions = Table(
    "role_permissions",
    Base.metadata,
    Column("role_id", ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
    Column("permission_id", ForeignKey("permissions.id", ondelete="CASCADE"), primary_key=True),
)


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    roles: Mapped[list["Role"]] = relationship(secondary=user_roles, back_populates="users", lazy="selectin")
    refresh_tokens: Mapped[list["RefreshToken"]] = relationship(back_populates="user", cascade="all, delete-orphan")

    @property
    def role_names(self) -> list[str]:
        return [r.name for r in self.roles]


class Role(Base):
    __tablename__ = "roles"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    description: Mapped[str] = mapped_column(String(255), default="")

    users: Mapped[list["User"]] = relationship(secondary=user_roles, back_populates="roles")
    permissions: Mapped[list["Permission"]] = relationship(
        secondary=role_permissions, back_populates="roles", lazy="selectin"
    )


class Permission(Base):
    __tablename__ = "permissions"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    description: Mapped[str] = mapped_column(String(255), default="")

    roles: Mapped[list["Role"]] = relationship(secondary=role_permissions, back_populates="permissions")


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id: Mapped[int] = mapped_column(primary_key=True)
    jti: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    revoked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)

    user: Mapped["User"] = relationship(back_populates="refresh_tokens")


# --------------------------------------------------------------------------- #
# Templates
# --------------------------------------------------------------------------- #
class Template(TimestampMixin, Base):
    __tablename__ = "templates"
    __table_args__ = (Index("ix_templates_channel_status", "channel", "status"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    channel: Mapped[str] = mapped_column(String(20), nullable=False)  # email|sms|push
    category: Mapped[str] = mapped_column(String(100), default="general", index=True)
    status: Mapped[str] = mapped_column(String(20), default="draft", nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    # Email
    subject: Mapped[str | None] = mapped_column(String(500), nullable=True)
    preheader: Mapped[str | None] = mapped_column(String(500), nullable=True)
    html_content: Mapped[str | None] = mapped_column(Text, nullable=True)
    # SMS
    text_content: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Push
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    body: Mapped[str | None] = mapped_column(Text, nullable=True)
    image_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    deep_link: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    # Push action buttons: [{"label": "...", "action": "..."}]
    buttons: Mapped[list | None] = mapped_column(JSON, nullable=True)

    # Declared personalization variables, e.g. ["first_name", "city"]
    variables: Mapped[list | None] = mapped_column(JSON, default=list)
    created_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)


class TemplateVersion(TimestampMixin, Base):
    """Immutable snapshot of a template at a point in time (versioning)."""

    __tablename__ = "template_versions"

    id: Mapped[int] = mapped_column(primary_key=True)
    template_id: Mapped[int] = mapped_column(ForeignKey("templates.id", ondelete="CASCADE"), index=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    snapshot: Mapped[dict] = mapped_column(JSON, nullable=False)


# --------------------------------------------------------------------------- #
# Contacts, custom fields, consent
# --------------------------------------------------------------------------- #
class Contact(TimestampMixin, Base):
    __tablename__ = "contacts"
    __table_args__ = (
        UniqueConstraint("email", name="uq_contacts_email"),
        Index("ix_contacts_country", "country"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str | None] = mapped_column(String(255), index=True, nullable=True)
    phone: Mapped[str | None] = mapped_column(String(50), index=True, nullable=True)
    device_token: Mapped[str | None] = mapped_column(String(512), nullable=True)
    first_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    last_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    country: Mapped[str | None] = mapped_column(String(2), nullable=True)
    timezone: Mapped[str | None] = mapped_column(String(64), default="UTC")
    tags: Mapped[list | None] = mapped_column(JSON, default=list)
    # Arbitrary custom field values: {"plan": "pro", "ltv": 1234}
    attributes: Mapped[dict | None] = mapped_column(JSON, default=dict)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    consents: Mapped[list["Consent"]] = relationship(back_populates="contact", cascade="all, delete-orphan")


class ContactCustomField(Base):
    """Definition of a custom contact attribute (schema for ``Contact.attributes``)."""

    __tablename__ = "contact_custom_fields"

    id: Mapped[int] = mapped_column(primary_key=True)
    key: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    label: Mapped[str] = mapped_column(String(255), nullable=False)
    field_type: Mapped[str] = mapped_column(String(20), default="string")  # string|number|bool|date
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)


class Consent(TimestampMixin, Base):
    __tablename__ = "consents"
    __table_args__ = (UniqueConstraint("contact_id", "channel", name="uq_consent_contact_channel"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    contact_id: Mapped[int] = mapped_column(ForeignKey("contacts.id", ondelete="CASCADE"), index=True)
    channel: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="subscribed", nullable=False)
    source: Mapped[str | None] = mapped_column(String(100), nullable=True)  # import|signup|stop|unsubscribe
    updated_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)

    contact: Mapped["Contact"] = relationship(back_populates="consents")


# --------------------------------------------------------------------------- #
# Segments
# --------------------------------------------------------------------------- #
class Segment(TimestampMixin, Base):
    __tablename__ = "segments"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[str] = mapped_column(String(500), default="")
    # Rule tree: {"op": "AND", "rules": [{"field","operator","value"}, {nested group}]}
    definition: Mapped[dict] = mapped_column(JSON, default=dict)
    is_dynamic: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    cached_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)

    rules: Mapped[list["SegmentRule"]] = relationship(back_populates="segment", cascade="all, delete-orphan")


class SegmentRule(Base):
    """Normalized representation of a single rule (also stored in Segment.definition)."""

    __tablename__ = "segment_rules"

    id: Mapped[int] = mapped_column(primary_key=True)
    segment_id: Mapped[int] = mapped_column(ForeignKey("segments.id", ondelete="CASCADE"), index=True)
    field: Mapped[str] = mapped_column(String(100), nullable=False)
    operator: Mapped[str] = mapped_column(String(30), nullable=False)
    value: Mapped[str | None] = mapped_column(Text, nullable=True)
    group: Mapped[str] = mapped_column(String(10), default="AND")

    segment: Mapped["Segment"] = relationship(back_populates="rules")


# --------------------------------------------------------------------------- #
# Campaigns
# --------------------------------------------------------------------------- #
class Campaign(TimestampMixin, Base):
    __tablename__ = "campaigns"
    __table_args__ = (Index("ix_campaigns_status_scheduled", "status", "scheduled_at"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[str] = mapped_column(String(1000), default="")
    type: Mapped[str] = mapped_column(String(30), default="one_time", nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="draft", nullable=False, index=True)

    # Primary channel for single-channel campaigns; multi-channel uses steps.
    channel: Mapped[str | None] = mapped_column(String(20), nullable=True)
    template_id: Mapped[int | None] = mapped_column(ForeignKey("templates.id"), nullable=True)
    segment_id: Mapped[int | None] = mapped_column(ForeignKey("segments.id"), nullable=True)

    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    timezone: Mapped[str] = mapped_column(String(64), default="UTC")
    # iCal-like recurrence for recurring campaigns, e.g. {"freq":"DAILY","interval":1,"count":5}
    recurrence: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    next_run_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)

    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    created_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    approved_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    rejection_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)

    steps: Mapped[list["CampaignStep"]] = relationship(
        back_populates="campaign", cascade="all, delete-orphan", order_by="CampaignStep.step_order"
    )


class CampaignStep(Base):
    """A step in a drip / multi-channel campaign."""

    __tablename__ = "campaign_steps"

    id: Mapped[int] = mapped_column(primary_key=True)
    campaign_id: Mapped[int] = mapped_column(ForeignKey("campaigns.id", ondelete="CASCADE"), index=True)
    step_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    channel: Mapped[str] = mapped_column(String(20), nullable=False)
    template_id: Mapped[int | None] = mapped_column(ForeignKey("templates.id"), nullable=True)
    # Delay before this step relative to the previous one (drip), in hours.
    delay_hours: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    campaign: Mapped["Campaign"] = relationship(back_populates="steps")


# --------------------------------------------------------------------------- #
# Delivery & events
# --------------------------------------------------------------------------- #
class Delivery(Base):
    __tablename__ = "deliveries"
    __table_args__ = (
        Index("ix_deliveries_campaign_status", "campaign_id", "status"),
        Index("ix_deliveries_contact", "contact_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    campaign_id: Mapped[int] = mapped_column(ForeignKey("campaigns.id", ondelete="CASCADE"), index=True)
    step_id: Mapped[int | None] = mapped_column(ForeignKey("campaign_steps.id"), nullable=True)
    contact_id: Mapped[int] = mapped_column(ForeignKey("contacts.id", ondelete="CASCADE"), index=True)
    channel: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)
    provider: Mapped[str | None] = mapped_column(String(50), nullable=True)
    provider_message_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    rendered_subject: Mapped[str | None] = mapped_column(String(500), nullable=True)
    rendered_body: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False, index=True)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    events: Mapped[list["EventLog"]] = relationship(back_populates="delivery", cascade="all, delete-orphan")


class EventLog(Base):
    __tablename__ = "event_logs"
    __table_args__ = (
        Index("ix_event_logs_campaign_type", "campaign_id", "event_type"),
        Index("ix_event_logs_occurred", "occurred_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    delivery_id: Mapped[int | None] = mapped_column(ForeignKey("deliveries.id", ondelete="CASCADE"), index=True)
    campaign_id: Mapped[int] = mapped_column(ForeignKey("campaigns.id", ondelete="CASCADE"), index=True)
    contact_id: Mapped[int | None] = mapped_column(ForeignKey("contacts.id"), nullable=True)
    channel: Mapped[str] = mapped_column(String(20), nullable=False)
    event_type: Mapped[str] = mapped_column(String(30), nullable=False)
    event_metadata: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)

    delivery: Mapped["Delivery"] = relationship(back_populates="events")


# --------------------------------------------------------------------------- #
# Providers
# --------------------------------------------------------------------------- #
class ProviderConfig(TimestampMixin, Base):
    __tablename__ = "provider_configs"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False, unique=True)
    channel: Mapped[str] = mapped_column(String(20), nullable=False)
    provider_type: Mapped[str] = mapped_column(String(30), nullable=False)
    # Non-secret settings; secrets resolved from data/providers/*.json or env.
    config: Mapped[dict] = mapped_column(JSON, default=dict)
    mode: Mapped[str] = mapped_column(String(20), default="console")  # console|live
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_health_status: Mapped[str | None] = mapped_column(String(20), nullable=True)
    last_health_checked_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


# --------------------------------------------------------------------------- #
# Analytics, reports, audit
# --------------------------------------------------------------------------- #
class AnalyticsSnapshot(Base):
    """Pre-aggregated per-campaign daily metrics for fast dashboards."""

    __tablename__ = "analytics_snapshots"
    __table_args__ = (
        UniqueConstraint("campaign_id", "channel", "snapshot_date", name="uq_snapshot_campaign_date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    campaign_id: Mapped[int] = mapped_column(ForeignKey("campaigns.id", ondelete="CASCADE"), index=True)
    channel: Mapped[str] = mapped_column(String(20), nullable=False)
    snapshot_date: Mapped[str] = mapped_column(String(10), nullable=False)  # YYYY-MM-DD
    sent: Mapped[int] = mapped_column(Integer, default=0)
    delivered: Mapped[int] = mapped_column(Integer, default=0)
    opened: Mapped[int] = mapped_column(Integer, default=0)
    clicked: Mapped[int] = mapped_column(Integer, default=0)
    bounced: Mapped[int] = mapped_column(Integer, default=0)
    failed: Mapped[int] = mapped_column(Integer, default=0)
    unsubscribed: Mapped[int] = mapped_column(Integer, default=0)
    converted: Mapped[int] = mapped_column(Integer, default=0)
    replied: Mapped[int] = mapped_column(Integer, default=0)


class Report(TimestampMixin, Base):
    __tablename__ = "reports"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    report_type: Mapped[str] = mapped_column(String(50), default="campaign_performance")
    fmt: Mapped[str] = mapped_column("format", String(10), default="csv")
    schedule: Mapped[str] = mapped_column(String(20), default="none")
    filters: Mapped[dict | None] = mapped_column(JSON, default=dict)
    last_generated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    file_path: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    created_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)


class AuditLog(Base):
    __tablename__ = "audit_logs"
    __table_args__ = (Index("ix_audit_entity", "entity_type", "entity_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    user_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    action: Mapped[str] = mapped_column(String(100), nullable=False)  # e.g. campaign.create
    entity_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    entity_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    detail: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False, index=True)
