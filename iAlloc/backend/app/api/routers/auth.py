from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.core.security import create_access_token, hash_password, verify_password
from app.models import STAKEHOLDER_ROLES, System, User, UserRole
from app.schemas.schemas import LoginRequest, SelfRegister, Token, UserOut

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _authenticate(db: Session, email: str, password: str) -> User:
    user = db.scalar(select(User).where(User.email == email))
    if not user or not verify_password(password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account disabled")
    return user


def _token_for(user: User) -> Token:
    token = create_access_token(
        str(user.id), claims={"role": user.role.value, "system_id": user.system_id}
    )
    return Token(access_token=token, user=UserOut.model_validate(user))


@router.post("/login", response_model=Token)
def login(body: LoginRequest, db: Session = Depends(get_db)):
    return _token_for(_authenticate(db, body.email, body.password))


@router.post("/token", response_model=Token)
def token(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """OAuth2 password flow (also powers the Swagger 'Authorize' button)."""
    return _token_for(_authenticate(db, form.username, form.password))


@router.post("/register", response_model=Token)
def self_register(body: SelfRegister, db: Session = Depends(get_db)):
    """Public self-registration for stakeholders (applicants by default)."""
    if body.role not in STAKEHOLDER_ROLES:
        raise HTTPException(status_code=400, detail="Cannot self-register this role")
    system = db.get(System, body.system_id)
    if not system:
        raise HTTPException(status_code=404, detail="System not found")
    if db.scalar(select(User).where(User.email == body.email)):
        raise HTTPException(status_code=409, detail="Email already registered")
    user = User(
        email=body.email,
        full_name=body.full_name,
        hashed_password=hash_password(body.password),
        role=body.role,
        system_id=body.system_id,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return _token_for(user)


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return user
