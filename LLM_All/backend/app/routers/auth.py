from __future__ import annotations

from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from jose import jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.config import load_system_config, settings
from app.database import get_db
from app.dependencies import get_current_user
from app.models import Conversation, User
from app.schemas import TokenResponse, UserLogin

router = APIRouter()
_pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")


def _create_token(user_id: str, username: str, role: str) -> str:
    expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    return jwt.encode(
        {"sub": user_id, "username": username, "role": role, "exp": expire},
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )


@router.post("/login", response_model=TokenResponse)
def login(body: UserLogin, db: Session = Depends(get_db)) -> TokenResponse:
    username = body.username.strip()
    password = body.password

    # ── Admin path ────────────────────────────────────────────────────────────
    if username == settings.ADMIN_USERNAME:
        if password != settings.ADMIN_PASSWORD:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

        user = db.query(User).filter(User.username == username).first()
        if not user:
            user = User(
                username=username,
                password_hash=_pwd.hash(password),
                role="admin",
            )
            db.add(user)
            db.commit()
            db.refresh(user)

        token = _create_token(user.id, user.username, user.role)
        return TokenResponse(
            access_token=token,
            conversation_id="",
            username=user.username,
            role=user.role,
        )

    # ── User path ─────────────────────────────────────────────────────────────
    user = db.query(User).filter(User.username == username).first()
    if not user:
        user = User(
            username=username,
            password_hash=_pwd.hash(password),
            role="user",
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    else:
        if not _pwd.verify(password, user.password_hash):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    # Every login spawns a fresh conversation
    config = load_system_config()
    conv = Conversation(
        user_id=user.id,
        title=f"Session {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}",
        llm_provider=config.get("active_llm", "openai"),
    )
    db.add(conv)
    db.commit()
    db.refresh(conv)

    token = _create_token(user.id, user.username, user.role)
    return TokenResponse(
        access_token=token,
        conversation_id=conv.id,
        username=user.username,
        role=user.role,
    )


@router.get("/me")
def me(current_user: User = Depends(get_current_user)) -> dict:
    return {"id": current_user.id, "username": current_user.username, "role": current_user.role}
