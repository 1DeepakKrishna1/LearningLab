"""Apply client-supplied credentials to outbound requests."""
from __future__ import annotations

import base64

from ..schemas import AuthConfig


def apply_auth(
    auth: AuthConfig | None,
    headers: dict[str, str],
    query: dict[str, object],
) -> tuple[dict[str, str], dict[str, object]]:
    """Return (headers, query) with auth material injected.

    Mutates copies, never the caller's dicts.
    """
    headers = dict(headers)
    query = dict(query)
    if auth is None or auth.type == "none":
        return headers, query

    if auth.type == "api_key" and auth.api_key and auth.api_key_name:
        if auth.api_key_location == "query":
            query[auth.api_key_name] = auth.api_key
        else:
            headers[auth.api_key_name] = auth.api_key

    elif auth.type == "bearer" and auth.token:
        token = auth.token
        prefix = "" if token.lower().startswith("bearer ") else "Bearer "
        headers["Authorization"] = f"{prefix}{token}"

    elif auth.type == "basic" and auth.username is not None:
        raw = f"{auth.username}:{auth.password or ''}".encode("utf-8")
        headers["Authorization"] = "Basic " + base64.b64encode(raw).decode("ascii")

    return headers, query
