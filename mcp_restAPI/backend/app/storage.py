"""In-memory storage for parsed specs and chat sessions.

This is deliberately a thin abstraction so it can be swapped for a database
(Postgres / Redis) without touching the services. State is process-local;
for a multi-worker deployment, back these with a shared store.
"""
from __future__ import annotations

import threading
import uuid
from typing import Any

from .openapi.parser import ParsedSpec
from .schemas import AuthConfig, PendingApproval, SpecSummary


class SpecStore:
    """Holds parsed specs keyed by a generated id."""

    def __init__(self) -> None:
        self._specs: dict[str, ParsedSpec] = {}
        self._sources: dict[str, str] = {}
        self._lock = threading.Lock()

    def add(self, parsed: ParsedSpec, source: str) -> str:
        spec_id = uuid.uuid4().hex[:12]
        with self._lock:
            self._specs[spec_id] = parsed
            self._sources[spec_id] = source
        return spec_id

    def replace(self, spec_id: str, parsed: ParsedSpec, source: str) -> None:
        with self._lock:
            self._specs[spec_id] = parsed
            self._sources[spec_id] = source

    def get(self, spec_id: str) -> ParsedSpec | None:
        return self._specs.get(spec_id)

    def source(self, spec_id: str) -> str:
        return self._sources.get(spec_id, "")

    def delete(self, spec_id: str) -> bool:
        with self._lock:
            existed = self._specs.pop(spec_id, None) is not None
            self._sources.pop(spec_id, None)
        return existed

    def summary(self, spec_id: str) -> SpecSummary | None:
        parsed = self._specs.get(spec_id)
        if parsed is None:
            return None
        return SpecSummary(
            id=spec_id,
            title=parsed.title,
            version=parsed.version,
            openapi_version=parsed.openapi_version,
            base_url=parsed.base_url,
            source=self._sources.get(spec_id, ""),
            operation_count=len(parsed.operations),
            security_schemes=parsed.security_schemes,
        )

    def list_summaries(self) -> list[SpecSummary]:
        return [s for s in (self.summary(sid) for sid in list(self._specs)) if s]


class Session:
    """Per-conversation state held server-side."""

    def __init__(self, session_id: str, spec_id: str) -> None:
        self.id = session_id
        self.spec_id = spec_id
        # OpenAI chat message history (list of role/content dicts).
        self.messages: list[dict[str, Any]] = []
        self.auth: AuthConfig = AuthConfig()
        # Approvals awaiting a human decision, keyed by approval_id.
        self.pending_approvals: dict[str, PendingApproval] = {}
        # Executor kwargs stashed for a pending approval, keyed by approval_id.
        self.pending_calls: dict[str, dict[str, Any]] = {}


class SessionStore:
    def __init__(self) -> None:
        self._sessions: dict[str, Session] = {}
        self._lock = threading.Lock()

    def get_or_create(self, session_id: str | None, spec_id: str) -> Session:
        with self._lock:
            if session_id and session_id in self._sessions:
                return self._sessions[session_id]
            sid = session_id or uuid.uuid4().hex
            session = Session(sid, spec_id)
            self._sessions[sid] = session
            return session

    def get(self, session_id: str) -> Session | None:
        return self._sessions.get(session_id)


# Module-level singletons (simple DI for the app).
spec_store = SpecStore()
session_store = SessionStore()
