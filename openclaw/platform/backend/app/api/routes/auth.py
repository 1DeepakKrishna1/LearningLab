"""Authentication & user-management routes."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from ...domain.user import LoginRequest, TokenResponse, UserCreate, UserPublic
from ...services.auth_service import AuthError
from ..deps import ContainerDep, CurrentUser, require

router = APIRouter(tags=["auth"])


@router.post("/auth/login", response_model=TokenResponse)
async def login(body: LoginRequest, container: ContainerDep) -> TokenResponse:
    try:
        return await container.auth_service.login(body)
    except AuthError as exc:
        raise HTTPException(401, str(exc)) from exc


@router.get("/auth/me", response_model=UserPublic)
async def me(user: CurrentUser) -> UserPublic:
    return UserPublic.of(user)


@router.get("/auth/users", response_model=list[UserPublic],
            dependencies=[Depends(require("user:manage"))])
async def list_users(container: ContainerDep) -> list[UserPublic]:
    return await container.auth_service.list_users()


@router.post("/auth/users", response_model=UserPublic,
             dependencies=[Depends(require("user:manage"))])
async def create_user(body: UserCreate, container: ContainerDep) -> UserPublic:
    try:
        return await container.auth_service.create_user(body)
    except AuthError as exc:
        raise HTTPException(400, str(exc)) from exc
