"""
Authentication helpers supporting TWO auth types:

  1. API Key  -> send header:  X-API-Key: <key>
  2. JWT      -> send header:  Authorization: Bearer <token>
                 (obtain a token from POST /auth/login)

Either one is accepted on protected endpoints.

Configuration (environment variables):
  API_KEY     default "my-secret-api-key"
  JWT_SECRET  default "my-super-secret-jwt-key-change-me"
  AUTH_USER   default "admin"
  AUTH_PASS   default "password"
"""
import os
import time

from dotenv import load_dotenv

# Load a .env file sitting next to this server (if present) so AUTH_ENABLED,
# API_KEY, PORT, etc. can be configured without exporting env vars manually.
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

import jwt
from fastapi import HTTPException, Security
from fastapi.security import (
    APIKeyHeader,
    HTTPAuthorizationCredentials,
    HTTPBearer,
)
from pydantic import BaseModel

def _flag(name: str, default: str = "true") -> bool:
    return os.getenv(name, default).strip().lower() in ("1", "true", "yes", "on")


# When AUTH_ENABLED is false the API runs completely open (no key / token needed).
AUTH_ENABLED = _flag("AUTH_ENABLED", "true")
API_KEY = os.getenv("API_KEY", "my-secret-api-key")
JWT_SECRET = os.getenv("JWT_SECRET", "my-super-secret-jwt-key-change-me")
JWT_ALG = "HS256"
JWT_EXP_SECONDS = int(os.getenv("JWT_EXP_SECONDS", "3600"))
AUTH_USER = os.getenv("AUTH_USER", "admin")
AUTH_PASS = os.getenv("AUTH_PASS", "password")

api_key_scheme = APIKeyHeader(name="X-API-Key", auto_error=False)
bearer_scheme = HTTPBearer(auto_error=False)


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int = JWT_EXP_SECONDS


def create_token(username: str) -> str:
    now = int(time.time())
    payload = {"sub": username, "iat": now, "exp": now + JWT_EXP_SECONDS}
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALG)


def login(req: LoginRequest) -> TokenResponse:
    if req.username != AUTH_USER or req.password != AUTH_PASS:
        raise HTTPException(status_code=401, detail="Invalid username or password")
    return TokenResponse(access_token=create_token(req.username))


def require_auth(
    api_key: str = Security(api_key_scheme),
    creds: HTTPAuthorizationCredentials = Security(bearer_scheme),
) -> dict:
    """Accept EITHER a valid API key OR a valid JWT bearer token.

    If AUTH_ENABLED is false this is a no-op and every request is allowed.
    """
    if not AUTH_ENABLED:
        return {"auth": "disabled"}

    if api_key is not None:
        if api_key == API_KEY:
            return {"auth": "api_key"}
        raise HTTPException(status_code=401, detail="Invalid API key")

    if creds is not None:
        try:
            payload = jwt.decode(creds.credentials, JWT_SECRET, algorithms=[JWT_ALG])
            return {"auth": "jwt", "sub": payload.get("sub")}
        except jwt.PyJWTError:
            raise HTTPException(status_code=401, detail="Invalid or expired token")

    raise HTTPException(
        status_code=401,
        detail="Not authenticated: provide 'X-API-Key' header or 'Authorization: Bearer <token>'",
    )
