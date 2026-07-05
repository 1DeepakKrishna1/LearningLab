"""Authentication & user management service."""
from __future__ import annotations

from ..config import Settings
from ..domain.enums import Role
from ..domain.user import LoginRequest, TokenResponse, User, UserCreate, UserPublic
from ..logging_setup import get_logger
from ..security.jwt_handler import JwtError, JwtHandler
from ..security.passwords import hash_password, verify_password
from ..storage.repository import Repository

logger = get_logger("service.auth")


class AuthError(Exception):
    pass


class AuthService:
    def __init__(self, repo: Repository[User], jwt: JwtHandler, settings: Settings) -> None:
        self._repo = repo
        self._jwt = jwt
        self._settings = settings

    async def bootstrap_admin(self) -> None:
        """Seed the first admin account if no users exist."""
        if await self._repo.count() > 0:
            return
        admin = User(
            email=self._settings.bootstrap_admin_email,
            name="Administrator",
            password_hash=hash_password(self._settings.bootstrap_admin_password),
            role=Role.ADMIN,
        )
        await self._repo.add(admin)
        logger.info("Seeded bootstrap admin: %s", admin.email)

    async def _by_email(self, email: str) -> User | None:
        users = await self._repo.find(lambda u: u.email.lower() == email.lower())
        return users[0] if users else None

    async def login(self, req: LoginRequest) -> TokenResponse:
        user = await self._by_email(req.email)
        if not user or not user.active or not verify_password(req.password, user.password_hash):
            raise AuthError("Invalid email or password.")
        token = self._jwt.encode({"sub": user.id, "email": user.email, "role": user.role.value})
        return TokenResponse(access_token=token, user=UserPublic.of(user))

    async def create_user(self, data: UserCreate) -> UserPublic:
        if await self._by_email(data.email):
            raise AuthError("A user with that email already exists.")
        user = User(email=data.email, name=data.name, role=data.role,
                    password_hash=hash_password(data.password))
        await self._repo.add(user)
        return UserPublic.of(user)

    async def list_users(self) -> list[UserPublic]:
        return [UserPublic.of(u) for u in await self._repo.list()]

    async def user_from_token(self, token: str) -> User:
        try:
            claims = self._jwt.decode(token)
        except JwtError as exc:
            raise AuthError(str(exc)) from exc
        user = await self._repo.get(claims.get("sub", ""))
        if not user or not user.active:
            raise AuthError("User not found or inactive.")
        return user
