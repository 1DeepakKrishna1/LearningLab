"""Load raw OpenAPI/Swagger documents from URLs or uploaded text.

A common gotcha is that users paste the *Swagger UI* page (e.g.
``http://localhost:8001/docs``) rather than the machine-readable spec. That
page is HTML; the actual document usually lives at ``/openapi.json`` (FastAPI),
``/v3/api-docs`` (Springdoc), ``/swagger/v1/swagger.json`` (ASP.NET), etc. So
when a fetched URL is not itself a spec, we try to discover the real spec URL
from the page's embedded config and from conventional fallback paths.
"""
from __future__ import annotations

import json
import re
from typing import Any
from urllib.parse import urljoin, urlparse

import httpx
import yaml

# Substrings that suggest a URL points at a spec document.
_SPEC_HINTS = ("openapi", "swagger", "api-docs", "api_docs", "apidocs")

# `url: "..."`, `spec-url="..."`, `specUrl: '...'` in Swagger UI / Redoc / RapiDoc.
_URL_IN_HTML = re.compile(
    r"""(?:spec[-_]?url|url)\s*[:=]\s*["']([^"'\s>]+)["']""", re.IGNORECASE
)
# Springdoc / Swagger UI may reference a config endpoint that lists the specs.
_CONFIG_URL_IN_HTML = re.compile(
    r"""config[-_]?url\s*[:=]\s*["']([^"'\s>]+)["']""", re.IGNORECASE
)

# Conventional spec locations to probe relative to a UI URL.
_CONVENTIONAL_NAMES = (
    "openapi.json",
    "openapi.yaml",
    "swagger.json",
    "v3/api-docs",
    "v2/api-docs",
    "api-docs",
    "swagger/v1/swagger.json",
    "docs/openapi.json",
)
# UI path suffixes to strip when deriving a base path.
_UI_SUFFIXES = (
    "/docs",
    "/swagger-ui.html",
    "/swagger-ui",
    "/swagger",
    "/redoc",
    "/api-docs",
)


class SpecLoadError(Exception):
    """Raised when a spec cannot be fetched or parsed into a dict."""


def parse_spec_text(content: str) -> dict[str, Any]:
    """Parse spec text as JSON, falling back to YAML.

    OpenAPI specs are valid YAML whether written as JSON or YAML, so a single
    YAML parse would suffice, but trying JSON first gives clearer errors and is
    faster for the common JSON case.
    """
    content = content.strip()
    if not content:
        raise SpecLoadError("Spec content is empty.")
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        pass
    try:
        loaded = yaml.safe_load(content)
    except yaml.YAMLError as exc:  # pragma: no cover - passthrough
        raise SpecLoadError(f"Could not parse spec as JSON or YAML: {exc}") from exc
    if not isinstance(loaded, dict):
        raise SpecLoadError("Parsed spec is not a JSON/YAML object.")
    return loaded


def _try_parse(text: str) -> dict[str, Any] | None:
    """Parse text into a dict, returning None instead of raising."""
    try:
        return parse_spec_text(text)
    except SpecLoadError:
        return None


def _looks_like_spec(data: Any) -> bool:
    return isinstance(data, dict) and any(k in data for k in ("openapi", "swagger", "paths"))


def _urls_from_config(config: Any) -> list[str]:
    """Extract spec URLs from a Swagger UI config object.

    Handles both ``{"url": "/v3/api-docs"}`` and the multi-spec
    ``{"urls": [{"url": "...", "name": "..."}]}`` shapes.
    """
    if not isinstance(config, dict):
        return []
    out: list[str] = []
    urls = config.get("urls")
    if isinstance(urls, list):
        for item in urls:
            if isinstance(item, dict) and isinstance(item.get("url"), str):
                out.append(item["url"])
            elif isinstance(item, str):
                out.append(item)
    if isinstance(config.get("url"), str):
        out.append(config["url"])
    return out


def _spec_urls_from_html(html: str) -> list[str]:
    """Pull plausible spec URLs out of a Swagger UI / Redoc HTML page."""
    found = []
    for match in _URL_IN_HTML.findall(html):
        lowered = match.lower()
        if lowered.endswith((".json", ".yaml", ".yml")) or any(h in lowered for h in _SPEC_HINTS):
            found.append(match)
    return found


def _conventional_candidates(url: str) -> list[str]:
    """Derive conventional spec URLs from a UI page URL."""
    parsed = urlparse(url)
    origin = f"{parsed.scheme}://{parsed.netloc}"
    path = parsed.path.rstrip("/")
    for suffix in _UI_SUFFIXES:
        if path.endswith(suffix):
            path = path[: -len(suffix)]
            break
    candidates: list[str] = []
    for name in _CONVENTIONAL_NAMES:
        if path:
            candidates.append(f"{origin}{path}/{name}")
        candidates.append(f"{origin}/{name}")
    return candidates


async def _get(client: httpx.AsyncClient, url: str) -> httpx.Response:
    resp = await client.get(
        url, headers={"Accept": "application/json, application/yaml, text/html, */*"}
    )
    resp.raise_for_status()
    return resp


async def fetch_spec_from_url(url: str, timeout: float = 30.0) -> dict[str, Any]:
    """Fetch a spec from a URL, discovering the real spec behind a UI page."""
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        try:
            resp = await _get(client, url)
        except httpx.HTTPError as exc:
            raise SpecLoadError(f"Failed to fetch spec from {url}: {exc}") from exc

        data = _try_parse(resp.text)
        if _looks_like_spec(data):
            return data  # type: ignore[return-value]

        # Not a spec itself — treat as a UI page and discover the spec URL.
        candidates: list[str] = []
        seen: set[str] = set()

        def add(raw: str, base: str = url) -> None:
            full = urljoin(base, raw)
            if full and full not in seen:
                seen.add(full)
                candidates.append(full)

        # 1. The fetched body might already be a Swagger UI config object.
        for u in _urls_from_config(data):
            add(u)
        # 2. A configUrl referenced by the HTML -> fetch it, then read its urls.
        for cfg_ref in _CONFIG_URL_IN_HTML.findall(resp.text):
            cfg_url = urljoin(url, cfg_ref)
            try:
                cfg = _try_parse((await _get(client, cfg_url)).text)
            except httpx.HTTPError:
                cfg = None
            for u in _urls_from_config(cfg):
                add(u, base=cfg_url)
        # 3. Spec URLs embedded directly in the HTML.
        for u in _spec_urls_from_html(resp.text):
            add(u)
        # 4. Conventional fallback locations.
        for u in _conventional_candidates(url):
            add(u)

        for candidate in candidates:
            try:
                cand_resp = await _get(client, candidate)
            except httpx.HTTPError:
                continue
            cand_data = _try_parse(cand_resp.text)
            if _looks_like_spec(cand_data):
                return cand_data  # type: ignore[return-value]

    hint = candidates[:5]
    raise SpecLoadError(
        f"{url} did not return an OpenAPI document — it looks like a Swagger UI/Redoc "
        f"page. I searched {len(candidates)} likely spec locations"
        + (f" (e.g. {', '.join(hint)})" if hint else "")
        + " without finding one. Please paste the direct spec URL, which is usually "
        "/openapi.json (FastAPI), /v3/api-docs (Springdoc), or /swagger/v1/swagger.json."
    )
