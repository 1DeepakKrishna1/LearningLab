"""Human-in-the-loop approval domain models."""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from .common import iso, new_id
from .enums import ApprovalChannel, ApprovalStatus


class Approval(BaseModel):
    """An approval request raised by an Approval node (persisted in approvals.json)."""

    id: str = Field(default_factory=new_id)
    execution_id: str
    workflow_id: str
    node_id: str
    title: str = "Approval required"
    description: str = ""
    channel: ApprovalChannel = ApprovalChannel.UI
    approvers: list[str] = Field(default_factory=list)
    status: ApprovalStatus = ApprovalStatus.PENDING
    payload: dict[str, Any] = Field(default_factory=dict)
    decided_by: str | None = None
    comment: str | None = None
    created_at: str = Field(default_factory=iso)
    decided_at: str | None = None


class ApprovalDecision(BaseModel):
    """The body posted to /approval/respond."""

    approval_id: str
    decision: ApprovalStatus
    comment: str | None = None
