from __future__ import annotations
from datetime import datetime
from typing import Any, Optional
from pydantic import BaseModel, field_validator


# ── Auth ─────────────────────────────────────────────────────────────────────

class UserLogin(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    conversation_id: str
    username: str
    role: str


# ── Chat ─────────────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str

    @field_validator("message")
    @classmethod
    def message_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Message cannot be empty")
        return v


class FollowUp(BaseModel):
    text: str
    query: str


class TokensConsumed(BaseModel):
    input: int
    output: int
    total: int


class ChatResponse(BaseModel):
    conversation_id: str
    message_id: str
    query: str
    response: str
    follow_ups: list[FollowUp]
    tokens_consumed: TokensConsumed
    time_taken: float
    guardrail_triggered: bool
    timestamp: datetime


# ── Messages / Conversations ──────────────────────────────────────────────────

class MessageOut(BaseModel):
    id: str
    role: str
    content: str
    tokens_in: int
    tokens_out: int
    time_taken: float
    guardrail_triggered: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class ConversationOut(BaseModel):
    id: str
    user_id: str
    username: str
    title: str
    llm_provider: Optional[str]
    message_count: int
    created_at: datetime
    updated_at: datetime


class ConversationDetail(ConversationOut):
    messages: list[MessageOut]
    summary: Optional[str]


# ── Admin: API Keys ───────────────────────────────────────────────────────────

class ApiKeysOut(BaseModel):
    openai: str
    anthropic: str
    google: str
    groq: str


class ApiKeysUpdate(BaseModel):
    openai: Optional[str] = None
    anthropic: Optional[str] = None
    google: Optional[str] = None
    groq: Optional[str] = None


# ── Admin: System Config ──────────────────────────────────────────────────────

class SystemConfigOut(BaseModel):
    active_llm: str
    models: dict[str, str]
    system_prompt: str
    context_window: int


class SystemConfigUpdate(BaseModel):
    active_llm: str
    models: Optional[dict[str, str]] = None
    system_prompt: str
    context_window: Optional[int] = 5


# ── Admin: Guardrails ─────────────────────────────────────────────────────────

class GuardrailRule(BaseModel):
    id: str
    name: str
    description: str
    enabled: bool
    type: str
    keywords: list[str] = []
    response: str


class GuardrailsOut(BaseModel):
    enabled: bool
    rules: list[GuardrailRule]


class GuardrailsUpdate(BaseModel):
    enabled: bool
    rules: list[GuardrailRule]


# ── Admin: Analytics ──────────────────────────────────────────────────────────

class AnalyticsOut(BaseModel):
    conversation_id: str
    username: str
    total_messages: int
    user_messages: int
    assistant_messages: int
    total_tokens: int
    avg_tokens_per_response: float
    avg_response_time: float
    total_time: float
    guardrail_triggers: int
    session_duration_minutes: float
    llm_provider: Optional[str]
    created_at: datetime


class SummaryOut(BaseModel):
    conversation_id: str
    summary: str
    generated_at: datetime


class InsightsOut(BaseModel):
    conversation_id: str
    insights: list[str]
    sentiment: str
    topics: list[str]
    generated_at: datetime
