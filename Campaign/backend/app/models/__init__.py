"""SQLAlchemy ORM models.

All models are defined in :mod:`app.models.models` and re-exported here so that
``from app.models import User`` works and Alembic autogenerate sees a single
metadata object.
"""
from app.models.models import (  # noqa: F401
    AnalyticsSnapshot,
    AuditLog,
    Campaign,
    CampaignStep,
    Consent,
    Contact,
    ContactCustomField,
    Delivery,
    EventLog,
    Permission,
    ProviderConfig,
    RefreshToken,
    Report,
    Role,
    Segment,
    SegmentRule,
    Template,
    TemplateVersion,
    User,
    role_permissions,
    user_roles,
)

__all__ = [
    "User",
    "Role",
    "Permission",
    "RefreshToken",
    "Campaign",
    "CampaignStep",
    "Template",
    "TemplateVersion",
    "Contact",
    "ContactCustomField",
    "Segment",
    "SegmentRule",
    "Delivery",
    "ProviderConfig",
    "EventLog",
    "AnalyticsSnapshot",
    "Report",
    "AuditLog",
    "Consent",
    "user_roles",
    "role_permissions",
]
