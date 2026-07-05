from __future__ import annotations

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import decode_token
from app.models import System, User, UserRole

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/token", auto_error=True)


def get_current_user(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
) -> User:
    payload = decode_token(token)
    if not payload or "sub" not in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
        )
    user = db.get(User, int(payload["sub"]))
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found/inactive"
        )
    return user


def require_roles(*roles: UserRole):
    allowed = {r.value if isinstance(r, UserRole) else r for r in roles}

    def checker(user: User = Depends(get_current_user)) -> User:
        if user.role.value not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires one of roles: {sorted(allowed)}",
            )
        return user

    return checker


def get_product_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != UserRole.product_admin:
        raise HTTPException(status_code=403, detail="ProductAdmin only")
    return user


def get_system_for_user(
    system_id: int, user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> System:
    system = db.get(System, system_id)
    if not system:
        raise HTTPException(status_code=404, detail="System not found")
    if user.role == UserRole.product_admin:
        return system
    if user.system_id != system.id:
        raise HTTPException(
            status_code=403, detail="You do not belong to this system"
        )
    return system


def require_system_admin(
    system_id: int, user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> System:
    system = db.get(System, system_id)
    if not system:
        raise HTTPException(status_code=404, detail="System not found")
    if user.role == UserRole.product_admin:
        return system
    if user.role == UserRole.system_admin and user.system_id == system.id:
        return system
    raise HTTPException(status_code=403, detail="SystemAdmin of this system required")
