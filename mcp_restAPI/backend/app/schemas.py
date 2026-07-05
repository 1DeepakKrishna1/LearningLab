"""Pydantic models shared across the API and services."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


def _now() -> datetime:
    return datetime.now(timezone.utc)


# --------------------------------------------------------------------------- #
# OpenAPI domain
# --------------------------------------------------------------------------- #
class ParameterInfo(BaseModel):
    """A single request parameter (path / query / header / cookie)."""

    name: str
    location: Literal["path", "query", "header", "cookie"]
    required: bool = False
    description: str | None = None
    schema_: dict[str, Any] = Field(default_factory=dict, alias="schema")
    example: Any | None = None

    model_config = {"populate_by_name": True}


class Operation(BaseModel):
    """A normalized, LLM-friendly view of one OpenAPI operation."""

    operation_id: str
    method: str
    path: str
    summary: str = ""
    description: str = ""
    tags: list[str] = Field(default_factory=list)
    parameters: list[ParameterInfo] = Field(default_factory=list)
    request_body_schema: dict[str, Any] | None = None
    request_body_required: bool = False
    request_content_type: str | None = None
    responses: dict[str, str] = Field(default_factory=dict)

    def signature(self) -> str:
        return f"{self.method} {self.path}"


class SecurityScheme(BaseModel):
    """Authentication scheme declared by the spec (informational)."""

    name: str
    type: str
    scheme: str | None = None
    location: str | None = None
    header_name: str | None = None
    description: str | None = None


class SpecSummary(BaseModel):
    id: str
    title: str
    version: str
    openapi_version: str
    base_url: str
    source: str
    operation_count: int
    security_schemes: list[SecurityScheme] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=_now)


# --------------------------------------------------------------------------- #
# Ingestion requests
# --------------------------------------------------------------------------- #
class IngestUrlRequest(BaseModel):
    url: str
    base_url_override: str | None = None


class IngestTextRequest(BaseModel):
    content: str
    base_url_override: str | None = None
    filename: str | None = None


# --------------------------------------------------------------------------- #
# Auth configuration supplied by the client per spec
# --------------------------------------------------------------------------- #
class AuthConfig(BaseModel):
    """Credentials the executor injects into outbound requests."""

    type: Literal["none", "api_key", "bearer", "basic"] = "none"
    # api_key
    api_key: str | None = None
    api_key_name: str | None = None
    api_key_location: Literal["header", "query"] = "header"
    # bearer / jwt
    token: str | None = None
    # basic
    username: str | None = None
    password: str | None = None


# --------------------------------------------------------------------------- #
# Chat / agent
# --------------------------------------------------------------------------- #
class ChatRequest(BaseModel):
    session_id: str | None = None
    spec_id: str
    message: str
    auth: AuthConfig | None = None


class ApprovalDecisionRequest(BaseModel):
    session_id: str
    approval_id: str
    approved: bool
    reason: str | None = None


class PendingApproval(BaseModel):
    """An invocation paused awaiting human approval."""

    approval_id: str
    operation_id: str
    method: str
    url: str
    summary: str
    query: dict[str, Any] = Field(default_factory=dict)
    headers: dict[str, str] = Field(default_factory=dict)
    body: Any | None = None
    reason: str = "This action mutates data and requires approval."


class ApiCallRecord(BaseModel):
    """A record of an executed REST call, surfaced to the UI."""

    operation_id: str
    method: str
    url: str
    status_code: int | None = None
    ok: bool = False
    request_body: Any | None = None
    response_preview: Any | None = None
    error: str | None = None
    duration_ms: float | None = None
    timestamp: datetime = Field(default_factory=_now)


class ChatResponse(BaseModel):
    session_id: str
    # "message"   -> agent produced a final/clarifying assistant message
    # "approval"  -> agent is blocked on a pending approval
    status: Literal["message", "approval"] = "message"
    message: str = ""
    pending_approval: Optional[PendingApproval] = None
    api_calls: list[ApiCallRecord] = Field(default_factory=list)
