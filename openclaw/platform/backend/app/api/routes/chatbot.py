"""AI chatbot route."""
from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from ..deps import ContainerDep, CurrentUser

router = APIRouter(tags=["chatbot"])


class ChatRequest(BaseModel):
    message: str


@router.post("/chat")
async def chat(body: ChatRequest, container: ContainerDep, user: CurrentUser) -> dict:
    return await container.chatbot_service.chat(body.message, user_id=user.id)
