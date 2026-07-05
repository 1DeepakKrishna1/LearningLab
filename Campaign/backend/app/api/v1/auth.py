"""Authentication endpoints: login, refresh, logout, password reset, profile."""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select

from app.core.audit import record_audit
from app.core.config import settings
from app.core.deps import CurrentUser, DbSession
from app.core.rate_limit import login_rate_limit
from app.core.security import (
    REFRESH_TOKEN,
    RESET_TOKEN,
    JWTError,
    create_access_token,
    create_refresh_token,
    create_reset_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models import RefreshToken, User
from app.schemas.auth import (
    ChangePasswordRequest,
    PasswordResetConfirm,
    PasswordResetRequest,
    RefreshRequest,
    TokenResponse,
)
from app.schemas.common import Message
from app.schemas.user import UserOut

logger = logging.getLogger("app.auth")
router = APIRouter(prefix="/auth", tags=["Authentication"])


def _issue_tokens(db, user: User) -> TokenResponse:
    access = create_access_token(str(user.id), user.role_names)
    refresh, jti, expires = create_refresh_token(str(user.id))
    db.add(RefreshToken(jti=jti, user_id=user.id, expires_at=expires))
    db.commit()
    return TokenResponse(
        access_token=access,
        refresh_token=refresh,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post("/login", response_model=TokenResponse, dependencies=[Depends(login_rate_limit)])
def login(
    db: DbSession,
    request: Request,
    form: Annotated[OAuth2PasswordRequestForm, Depends()],
):
    """OAuth2 password flow. ``username`` field carries the email."""
    user = db.scalar(select(User).where(User.email == form.username.lower()))
    if not user or not verify_password(form.password, user.hashed_password):
        record_audit(db, action="auth.login_failed", detail={"email": form.username},
                     ip_address=request.client.host if request.client else None)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account disabled")

    user.last_login_at = datetime.now(timezone.utc)
    record_audit(db, action="auth.login", user=user, commit=False,
                 ip_address=request.client.host if request.client else None)
    return _issue_tokens(db, user)


@router.post("/refresh", response_model=TokenResponse)
def refresh_tokens(db: DbSession, payload: RefreshRequest):
    try:
        claims = decode_token(payload.refresh_token)
    except JWTError as exc:
        raise HTTPException(status_code=401, detail="Invalid refresh token") from exc
    if claims.get("type") != REFRESH_TOKEN:
        raise HTTPException(status_code=401, detail="Not a refresh token")

    jti = claims.get("jti")
    stored = db.scalar(select(RefreshToken).where(RefreshToken.jti == jti))
    # SQLite returns naive datetimes; normalize to naive UTC for comparison.
    now_naive = datetime.now(timezone.utc).replace(tzinfo=None)
    expires = stored.expires_at.replace(tzinfo=None) if stored else None
    if not stored or stored.revoked or (expires is not None and expires < now_naive):
        raise HTTPException(status_code=401, detail="Refresh token expired or revoked")

    user = db.get(User, int(claims["sub"]))
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or inactive")

    # Rotate: revoke the used refresh token.
    stored.revoked = True
    db.commit()
    return _issue_tokens(db, user)


@router.post("/logout", response_model=Message)
def logout(db: DbSession, user: CurrentUser, payload: RefreshRequest | None = None):
    """Revoke the supplied refresh token (or all of the user's tokens)."""
    if payload and payload.refresh_token:
        try:
            claims = decode_token(payload.refresh_token)
            stored = db.scalar(select(RefreshToken).where(RefreshToken.jti == claims.get("jti")))
            if stored:
                stored.revoked = True
        except JWTError:
            pass
    else:
        for token in user.refresh_tokens:
            token.revoked = True
    db.commit()
    return Message(message="Logged out")


@router.post("/password-reset/request", response_model=Message)
def request_password_reset(db: DbSession, payload: PasswordResetRequest):
    """Issue a reset token. In a self-hosted demo the token is logged (no SMTP)."""
    user = db.scalar(select(User).where(User.email == payload.email.lower()))
    if user:
        token = create_reset_token(str(user.id))
        # TODO: deliver via email provider. For local/demo we log it.
        logger.info("Password reset token for %s: %s", user.email, token)
    # Always return success to avoid account enumeration.
    return Message(message="If the account exists, a reset link has been sent.")


@router.post("/password-reset/confirm", response_model=Message)
def confirm_password_reset(db: DbSession, payload: PasswordResetConfirm):
    try:
        claims = decode_token(payload.token)
    except JWTError as exc:
        raise HTTPException(status_code=400, detail="Invalid or expired token") from exc
    if claims.get("type") != RESET_TOKEN:
        raise HTTPException(status_code=400, detail="Invalid token type")
    user = db.get(User, int(claims["sub"]))
    if not user:
        raise HTTPException(status_code=400, detail="Invalid token")
    user.hashed_password = hash_password(payload.new_password)
    for token in user.refresh_tokens:
        token.revoked = True
    record_audit(db, action="auth.password_reset", user=user, commit=False)
    db.commit()
    return Message(message="Password updated")


@router.get("/me", response_model=UserOut)
def me(user: CurrentUser):
    return user


@router.post("/change-password", response_model=Message)
def change_password(db: DbSession, user: CurrentUser, payload: ChangePasswordRequest):
    if not verify_password(payload.current_password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    user.hashed_password = hash_password(payload.new_password)
    record_audit(db, action="auth.change_password", user=user, commit=False)
    db.commit()
    return Message(message="Password changed")
