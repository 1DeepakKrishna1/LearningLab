"""Shared FastAPI dependencies: container access, current user, RBAC guards."""
from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Header, HTTPException, Request, status

from ..container import Container
from ..domain.user import User
from ..security.rbac import can


def get_container(request: Request) -> Container:
    return request.app.state.container


ContainerDep = Annotated[Container, Depends(get_container)]


async def current_user(
    container: ContainerDep,
    authorization: Annotated[str | None, Header()] = None,
) -> User:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Missing bearer token.")
    token = authorization.split(" ", 1)[1].strip()
    try:
        return await container.auth_service.user_from_token(token)
    except Exception as exc:  # AuthError / JwtError
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, str(exc)) from exc


CurrentUser = Annotated[User, Depends(current_user)]


def require(permission: str):
    """Return a dependency that enforces the given RBAC permission."""

    async def _guard(user: CurrentUser) -> User:
        if not can(user.role, permission):
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                f"Role '{user.role.value}' lacks permission '{permission}'.",
            )
        return user

    return _guard
