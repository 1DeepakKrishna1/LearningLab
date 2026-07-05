"""Enumerations shared across the domain."""
from __future__ import annotations

from enum import Enum


class Role(str, Enum):
    """RBAC roles, ordered most → least privileged via `level`."""

    ADMIN = "admin"
    DESIGNER = "designer"
    OPERATOR = "operator"
    VIEWER = "viewer"

    @property
    def level(self) -> int:
        return {"admin": 3, "designer": 2, "operator": 1, "viewer": 0}[self.value]

    def satisfies(self, required: "Role") -> bool:
        """True if this role is at least as privileged as `required`."""
        return self.level >= required.level


class AgentRole(str, Enum):
    SUPERVISOR = "supervisor"
    PLANNER = "planner"
    EXECUTOR = "executor"
    RESEARCHER = "researcher"
    REVIEWER = "reviewer"
    CUSTOM = "custom"


class AgentCapability(str, Enum):
    TOOL_CALLING = "tool_calling"
    MEMORY = "memory"
    COLLABORATION = "collaboration"
    DELEGATION = "delegation"
    REFLECTION = "reflection"
    PLANNING = "planning"


class WorkflowStatus(str, Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class ExecutionStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    WAITING_APPROVAL = "waiting_approval"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

    @property
    def is_terminal(self) -> bool:
        return self in {ExecutionStatus.COMPLETED, ExecutionStatus.FAILED,
                        ExecutionStatus.CANCELLED}


class NodeRunStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    WAITING = "waiting"


class ApprovalStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    CHANGES_REQUESTED = "changes_requested"
    ESCALATED = "escalated"


class ApprovalChannel(str, Enum):
    UI = "ui"
    EMAIL = "email"
    WHATSAPP = "whatsapp"


class NodeGroup(str, Enum):
    TRIGGER = "trigger"
    AGENT = "agent"
    LOGIC = "logic"
    TOOL = "tool"
    ACTION = "action"


class AuditActor(str, Enum):
    USER = "user"
    AGENT = "agent"
    SYSTEM = "system"
