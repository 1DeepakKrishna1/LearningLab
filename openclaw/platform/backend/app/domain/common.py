"""Common helpers for domain models: IDs and timestamps.

Note on time: the engine and services pass explicit timestamps where determinism
matters; `utcnow()` is the single source of "now" so it can be monkeypatched in tests.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone


def new_id() -> str:
    """Generate a new opaque entity id."""
    return uuid.uuid4().hex


def utcnow() -> datetime:
    """Timezone-aware current UTC time."""
    return datetime.now(timezone.utc)


def iso(dt: datetime | None = None) -> str:
    """ISO-8601 string for a datetime (defaults to now)."""
    return (dt or utcnow()).isoformat()
