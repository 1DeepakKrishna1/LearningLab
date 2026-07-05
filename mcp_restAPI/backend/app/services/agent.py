"""The LLM agent: turns natural language into planned, approved REST calls.

Design
------
The agent exposes four tools to the model and runs a tool-calling loop:

* ``search_endpoints``      - find relevant operations by natural language
* ``get_endpoint_details``  - inspect parameters / request body schema
* ``invoke_api``            - execute an operation (gated by human approval
                              for mutating methods)
* ``ask_user``              - request a missing parameter / clarification

Mutating calls pause the loop and surface a :class:`PendingApproval`. The
conversation resumes via :meth:`Agent.handle_approval` once the human decides.
``parallel_tool_calls`` is disabled so each assistant turn carries at most one
tool call, which keeps the pause/resume bookkeeping exact.
"""
from __future__ import annotations

import json
import uuid
from typing import Any

from ..config import get_settings
from ..openapi.parser import ParsedSpec
from ..schemas import (
    ApiCallRecord,
    AuthConfig,
    ChatResponse,
    Operation,
    PendingApproval,
)
from ..storage import Session
from . import llm
from .executor import MissingPathParameter, build_url, execute_operation
from .search import search_operations

_MAX_INLINE_OPS = 50

TOOLS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "search_endpoints",
            "description": (
                "Search the API catalog for operations relevant to a natural-language "
                "query. Use this to discover which endpoint(s) can fulfil the user's intent."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "What the user wants to do, e.g. 'create a customer'.",
                    }
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_endpoint_details",
            "description": (
                "Get the full parameter list and request-body schema for one operation. "
                "Call this before invoke_api to know which parameters are required."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "operation_id": {"type": "string"},
                },
                "required": ["operation_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "invoke_api",
            "description": (
                "Execute a REST operation. Provide path/query parameters, headers and a "
                "request body as needed. Mutating methods (POST/PUT/PATCH/DELETE) will be "
                "paused for human approval automatically — just call this normally."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "operation_id": {"type": "string"},
                    "path_params": {
                        "type": "object",
                        "description": "Values for path placeholders, e.g. {\"id\": 123}.",
                        "additionalProperties": True,
                    },
                    "query": {
                        "type": "object",
                        "description": "Query-string parameters.",
                        "additionalProperties": True,
                    },
                    "headers": {
                        "type": "object",
                        "description": "Extra request headers (auth is added automatically).",
                        "additionalProperties": True,
                    },
                    "body": {
                        "description": "Request body (object/array/string) for write methods.",
                    },
                },
                "required": ["operation_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "ask_user",
            "description": (
                "Ask the user for a missing required parameter or a clarification. "
                "Ask for one specific thing at a time. Use this instead of guessing."
            ),
            "parameters": {
                "type": "object",
                "properties": {"question": {"type": "string"}},
                "required": ["question"],
            },
        },
    },
]


def _operation_brief(op: Operation) -> str:
    summary = op.summary or op.description.split("\n")[0]
    summary = (summary[:100] + "…") if len(summary) > 100 else summary
    return f"- {op.operation_id} [{op.signature()}] {summary}".rstrip()


def _operation_details(op: Operation) -> dict[str, Any]:
    return {
        "operation_id": op.operation_id,
        "method": op.method,
        "path": op.path,
        "summary": op.summary,
        "description": op.description,
        "tags": op.tags,
        "parameters": [
            {
                "name": p.name,
                "in": p.location,
                "required": p.required,
                "schema": p.schema_,
                "description": p.description,
            }
            for p in op.parameters
        ],
        "request_body_required": op.request_body_required,
        "request_body_schema": op.request_body_schema,
        "responses": op.responses,
    }


class Agent:
    """Drives one user turn against a parsed spec for a given session."""

    def __init__(self, session: Session, parsed: ParsedSpec, auth: AuthConfig | None) -> None:
        self.session = session
        self.parsed = parsed
        self.auth = auth
        self.settings = get_settings()
        self.api_calls: list[ApiCallRecord] = []

    # -- public entry points ------------------------------------------------ #
    async def handle_message(self, text: str) -> ChatResponse:
        if not self.session.messages:
            self.session.messages.append({"role": "system", "content": self._system_prompt()})
        self.session.messages.append({"role": "user", "content": text})
        return await self._loop()

    async def handle_approval(self, approval_id: str, approved: bool, reason: str | None) -> ChatResponse:
        pending = self.session.pending_approvals.pop(approval_id, None)
        call = self.session.pending_calls.pop(approval_id, None)
        if pending is None or call is None:
            return ChatResponse(
                session_id=self.session.id,
                status="message",
                message="That approval request is no longer pending.",
            )

        if approved:
            op = self.parsed.get(call["operation_id"])
            record = await execute_operation(
                base_url=self.parsed.base_url,
                op=op,
                auth=self.auth,
                path_params=call["path_params"],
                query=call["query"],
                headers=call["headers"],
                body=call["body"],
            )
            self.api_calls.append(record)
            tool_content = _record_for_llm(record)
        else:
            note = f" Reason: {reason}" if reason else ""
            tool_content = json.dumps(
                {
                    "approved": False,
                    "message": f"The user REJECTED this {pending.method} action.{note} "
                    "Do not retry it. Offer alternatives or ask how to proceed.",
                }
            )

        # Resolve the dangling tool call from the paused assistant turn.
        self.session.messages.append(
            {"role": "tool", "tool_call_id": approval_id, "content": tool_content}
        )
        return await self._loop()

    # -- core loop ---------------------------------------------------------- #
    async def _loop(self) -> ChatResponse:
        for _ in range(self.settings.agent_max_steps):
            message = await llm.chat_completion(self.session.messages, TOOLS)
            self.session.messages.append(_assistant_to_dict(message))

            tool_calls = message.tool_calls or []
            if not tool_calls:
                return ChatResponse(
                    session_id=self.session.id,
                    status="message",
                    message=message.content or "",
                    api_calls=self.api_calls,
                )

            call = tool_calls[0]
            name = call.function.name
            args = _safe_json(call.function.arguments)

            if name == "ask_user":
                question = args.get("question", "Could you clarify your request?")
                self.session.messages.append(
                    {"role": "tool", "tool_call_id": call.id,
                     "content": json.dumps({"status": "asked_user", "question": question})}
                )
                return ChatResponse(
                    session_id=self.session.id,
                    status="message",
                    message=question,
                    api_calls=self.api_calls,
                )

            if name == "search_endpoints":
                result = self._tool_search(args.get("query", ""))
            elif name == "get_endpoint_details":
                result = self._tool_details(args.get("operation_id", ""))
            elif name == "invoke_api":
                paused = await self._tool_invoke(call.id, args)
                if paused is not None:
                    return paused  # awaiting human approval
                continue  # tool result already appended by _tool_invoke
            else:
                result = {"error": f"Unknown tool '{name}'."}

            self.session.messages.append(
                {"role": "tool", "tool_call_id": call.id, "content": json.dumps(result)}
            )

        # Loop budget exhausted.
        return ChatResponse(
            session_id=self.session.id,
            status="message",
            message=(
                "I reached the maximum number of reasoning steps without finishing. "
                "Please refine the request or break it into smaller steps."
            ),
            api_calls=self.api_calls,
        )

    # -- tool implementations ---------------------------------------------- #
    def _tool_search(self, query: str) -> dict[str, Any]:
        matches = search_operations(self.parsed, query, limit=8)
        return {
            "results": [
                {
                    "operation_id": op.operation_id,
                    "method": op.method,
                    "path": op.path,
                    "summary": op.summary or op.description[:120],
                    "tags": op.tags,
                }
                for op, _ in matches
            ]
        }

    def _tool_details(self, operation_id: str) -> dict[str, Any]:
        op = self.parsed.get(operation_id)
        if op is None:
            return {"error": f"No operation with id '{operation_id}'. Use search_endpoints."}
        return _operation_details(op)

    async def _tool_invoke(self, tool_call_id: str, args: dict[str, Any]) -> ChatResponse | None:
        """Execute or pause an invoke_api call.

        Returns a :class:`ChatResponse` if the call is paused for approval,
        otherwise ``None`` after appending the tool result to history.
        """
        operation_id = args.get("operation_id", "")
        op = self.parsed.get(operation_id)
        if op is None:
            self._append_tool_error(tool_call_id, f"No operation '{operation_id}'.")
            return None

        path_params = args.get("path_params") or {}
        query = args.get("query") or {}
        headers = args.get("headers") or {}
        body = args.get("body")

        # Validate path params early so the model can recover via ask_user.
        try:
            url = build_url(self.parsed.base_url, op, path_params)
        except MissingPathParameter as exc:
            self._append_tool_error(
                tool_call_id,
                f"Missing required path parameter '{exc}'. Ask the user for it.",
            )
            return None

        if op.method in self.settings.approval_required_methods:
            approval_id = tool_call_id  # 1:1 with the dangling tool call
            pending = PendingApproval(
                approval_id=approval_id,
                operation_id=op.operation_id,
                method=op.method,
                url=url,
                summary=op.summary or op.signature(),
                query=query,
                headers=headers,
                body=body,
            )
            self.session.pending_approvals[approval_id] = pending
            self.session.pending_calls[approval_id] = {
                "operation_id": op.operation_id,
                "path_params": path_params,
                "query": query,
                "headers": headers,
                "body": body,
            }
            return ChatResponse(
                session_id=self.session.id,
                status="approval",
                message=f"Approval required to run **{op.method} {op.path}**.",
                pending_approval=pending,
                api_calls=self.api_calls,
            )

        # Safe (read) method -> execute immediately.
        record = await execute_operation(
            base_url=self.parsed.base_url,
            op=op,
            auth=self.auth,
            path_params=path_params,
            query=query,
            headers=headers,
            body=body,
        )
        self.api_calls.append(record)
        self.session.messages.append(
            {"role": "tool", "tool_call_id": tool_call_id, "content": _record_for_llm(record)}
        )
        return None

    def _append_tool_error(self, tool_call_id: str, message: str) -> None:
        self.session.messages.append(
            {"role": "tool", "tool_call_id": tool_call_id, "content": json.dumps({"error": message})}
        )

    # -- prompt ------------------------------------------------------------- #
    def _system_prompt(self) -> str:
        ops = self.parsed.operations
        listing = "\n".join(_operation_brief(op) for op in ops[:_MAX_INLINE_OPS])
        more = (
            f"\n…and {len(ops) - _MAX_INLINE_OPS} more — use search_endpoints to find them."
            if len(ops) > _MAX_INLINE_OPS
            else ""
        )
        schemes = ", ".join(s.name for s in self.parsed.security_schemes) or "none declared"
        return (
            "You are an expert API agent. You fulfil user requests by calling the REST "
            f"API '{self.parsed.title}' (base URL {self.parsed.base_url or 'unknown'}).\n\n"
            "Operating rules:\n"
            "1. Identify the user's intent and the right operation(s). Use search_endpoints "
            "if unsure, and get_endpoint_details before invoking to learn required parameters.\n"
            "2. Extract parameter values from the user's message and the conversation. If a "
            "REQUIRED parameter is missing and cannot be inferred, call ask_user for that one "
            "specific value — never invent IDs, emails, or other data.\n"
            "3. For multi-step goals, plan and chain calls: use the output of earlier calls as "
            "input to later ones (e.g. search → create → use the new id).\n"
            "4. Write operations (POST/PUT/PATCH/DELETE) are automatically paused for human "
            "approval — just call invoke_api and the system handles it.\n"
            "5. After calls, explain the result to the user in plain language. On errors, "
            "reflect: fix parameters and retry, try an alternate endpoint, or ask the user.\n"
            "6. Never fabricate API responses or claim success you didn't observe.\n\n"
            f"Declared authentication: {schemes}.\n\n"
            f"Available operations ({len(ops)} total):\n{listing}{more}"
        )


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def _safe_json(raw: str | None) -> dict[str, Any]:
    if not raw:
        return {}
    try:
        value = json.loads(raw)
        return value if isinstance(value, dict) else {}
    except (json.JSONDecodeError, TypeError):
        return {}


def _assistant_to_dict(message: Any) -> dict[str, Any]:
    """Convert an OpenAI message object into a history-safe dict."""
    out: dict[str, Any] = {"role": "assistant", "content": message.content or ""}
    if message.tool_calls:
        out["tool_calls"] = [
            {
                "id": tc.id,
                "type": "function",
                "function": {"name": tc.function.name, "arguments": tc.function.arguments},
            }
            for tc in message.tool_calls
        ]
    return out


def _record_for_llm(record: ApiCallRecord) -> str:
    """Compact JSON of a call result for the model to reason over."""
    return json.dumps(
        {
            "operation_id": record.operation_id,
            "ok": record.ok,
            "status_code": record.status_code,
            "error": record.error,
            "response": record.response_preview,
        },
        default=str,
    )
