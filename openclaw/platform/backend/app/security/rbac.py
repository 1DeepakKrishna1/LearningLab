"""Role-based access control.

Permissions are coarse-grained verbs over resources; each maps to a minimum role.
Routes declare the permission they need; the dependency in ``api/deps.py`` enforces it.
"""
from __future__ import annotations

from ..domain.enums import Role

# permission -> minimum role required
PERMISSIONS: dict[str, Role] = {
    # workflows
    "workflow:read": Role.VIEWER,
    "workflow:run": Role.OPERATOR,
    "workflow:write": Role.DESIGNER,
    "workflow:delete": Role.DESIGNER,
    # executions
    "execution:read": Role.VIEWER,
    "execution:cancel": Role.OPERATOR,
    # agents
    "agent:read": Role.VIEWER,
    "agent:write": Role.DESIGNER,
    "agent:delete": Role.DESIGNER,
    # tools
    "tool:read": Role.VIEWER,
    "tool:execute": Role.OPERATOR,
    "tool:refresh": Role.DESIGNER,
    # approvals
    "approval:read": Role.VIEWER,
    "approval:decide": Role.OPERATOR,
    # audit / monitoring
    "audit:read": Role.OPERATOR,
    "monitoring:read": Role.VIEWER,
    # admin
    "user:manage": Role.ADMIN,
    "settings:write": Role.ADMIN,
    "settings:read": Role.OPERATOR,
}


def required_role(permission: str) -> Role:
    if permission not in PERMISSIONS:
        # Unknown permission → fail closed at the highest privilege.
        return Role.ADMIN
    return PERMISSIONS[permission]


def can(role: Role, permission: str) -> bool:
    return role.satisfies(required_role(permission))
