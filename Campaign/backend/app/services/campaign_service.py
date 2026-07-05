"""Campaign lifecycle state machine and transition helpers.

Lifecycle::

    draft ──submit──▶ pending_approval ──approve──▶ approved ──schedule──▶ scheduled
      ▲                     │                                                  │
      │                  reject                                            (due / send)
      └─────────────────────┘                                                 ▼
                                                                           sending
                                          ┌──────────┬──────────┬──────────────┤
                                       complete    fail       pause        cancel
                                          ▼          ▼          ▼              ▼
                                      completed   failed     paused        cancelled
    (most non-terminal states) ──archive──▶ archived
    paused ──resume──▶ scheduled
"""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import HTTPException, status

from app.models.enums import CampaignStatus as S

# Allowed transitions map.
ALLOWED: dict[str, set[str]] = {
    S.DRAFT.value: {S.PENDING_APPROVAL.value, S.ARCHIVED.value, S.CANCELLED.value},
    S.PENDING_APPROVAL.value: {S.APPROVED.value, S.DRAFT.value, S.CANCELLED.value},
    S.APPROVED.value: {S.SCHEDULED.value, S.SENDING.value, S.CANCELLED.value, S.DRAFT.value},
    S.SCHEDULED.value: {S.SENDING.value, S.PAUSED.value, S.CANCELLED.value, S.APPROVED.value},
    S.SENDING.value: {S.COMPLETED.value, S.FAILED.value, S.PAUSED.value, S.CANCELLED.value},
    S.PAUSED.value: {S.SCHEDULED.value, S.SENDING.value, S.CANCELLED.value, S.ARCHIVED.value},
    S.COMPLETED.value: {S.ARCHIVED.value},
    S.FAILED.value: {S.SCHEDULED.value, S.ARCHIVED.value, S.CANCELLED.value},
    S.CANCELLED.value: {S.ARCHIVED.value},
    S.ARCHIVED.value: set(),
}

TERMINAL = {S.COMPLETED.value, S.CANCELLED.value, S.ARCHIVED.value}
EDITABLE = {S.DRAFT.value, S.PENDING_APPROVAL.value}


def can_transition(current: str, target: str) -> bool:
    return target in ALLOWED.get(current, set())


def assert_transition(current: str, target: str) -> None:
    if not can_transition(current, target):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Illegal transition: {current} -> {target}",
        )


def assert_editable(current: str) -> None:
    if current not in EDITABLE:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Campaign in status '{current}' cannot be edited.",
        )


def now() -> datetime:
    return datetime.now(timezone.utc)
