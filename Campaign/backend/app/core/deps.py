"""FastAPI dependencies for authentication and role-based authorization."""
from __future__ import annotations

from collections.abc import Generator
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.security import ACCESS_TOKEN, JWTError, decode_token
from app.models import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_PREFIX}/auth/login")

CREDENTIALS_EXC = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"},
)


def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Annotated[Session, Depends(get_db)],
) -> User:
    try:
        payload = decode_token(token)
        if payload.get("type") != ACCESS_TOKEN:
            raise CREDENTIALS_EXC
        user_id = payload.get("sub")
        if user_id is None:
            raise CREDENTIALS_EXC
    except JWTError as exc:
        raise CREDENTIALS_EXC from exc

    user = db.get(User, int(user_id))
    if user is None or not user.is_active:
        raise CREDENTIALS_EXC
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
DbSession = Annotated[Session, Depends(get_db)]


def require_roles(*allowed: str):
    """Return a dependency enforcing that the user has at least one allowed role."""

    def checker(user: CurrentUser) -> User:
        if not set(allowed).intersection(user.role_names):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires one of roles: {', '.join(allowed)}",
            )
        return user

    return checker


# Convenience role gates
require_admin = require_roles("admin")
require_marketer = require_roles("admin", "marketer")
require_viewer = require_roles("admin", "marketer", "viewer")
