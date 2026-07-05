"""Normalize raw OpenAPI 2.0 / 3.x documents into a flat operation catalog.

The parser is intentionally tolerant: real-world specs are messy, so missing
fields degrade gracefully rather than raising.
"""
from __future__ import annotations

from typing import Any, Iterable
from urllib.parse import urljoin, urlparse

from ..schemas import Operation, ParameterInfo, SecurityScheme

HTTP_METHODS = ("get", "post", "put", "patch", "delete", "options", "head")
_MAX_REF_DEPTH = 50


class ParsedSpec:
    """In-memory representation of a parsed spec."""

    def __init__(
        self,
        *,
        title: str,
        version: str,
        openapi_version: str,
        base_url: str,
        operations: list[Operation],
        security_schemes: list[SecurityScheme],
        raw: dict[str, Any],
    ) -> None:
        self.title = title
        self.version = version
        self.openapi_version = openapi_version
        self.base_url = base_url
        self.operations = operations
        self.security_schemes = security_schemes
        self.raw = raw
        self._by_id = {op.operation_id: op for op in operations}

    def get(self, operation_id: str) -> Operation | None:
        return self._by_id.get(operation_id)


class _RefResolver:
    """Resolves local ``$ref`` pointers within a single document."""

    def __init__(self, root: dict[str, Any]) -> None:
        self.root = root

    def resolve(self, node: Any, _depth: int = 0) -> Any:
        if _depth > _MAX_REF_DEPTH:
            return {}
        if isinstance(node, dict):
            if "$ref" in node and isinstance(node["$ref"], str):
                target = self._lookup(node["$ref"])
                resolved = self.resolve(target, _depth + 1)
                # Merge sibling keys (allowed in OpenAPI 3.1) over the ref target.
                extras = {k: v for k, v in node.items() if k != "$ref"}
                if extras and isinstance(resolved, dict):
                    return {**resolved, **self.resolve(extras, _depth + 1)}
                return resolved
            return {k: self.resolve(v, _depth + 1) for k, v in node.items()}
        if isinstance(node, list):
            return [self.resolve(item, _depth + 1) for item in node]
        return node

    def _lookup(self, ref: str) -> Any:
        if not ref.startswith("#/"):
            # External refs are not supported; return an empty schema.
            return {}
        node: Any = self.root
        for part in ref[2:].split("/"):
            part = part.replace("~1", "/").replace("~0", "~")
            if isinstance(node, dict) and part in node:
                node = node[part]
            else:
                return {}
        return node


def _detect_base_url(spec: dict[str, Any], source_url: str | None) -> str:
    """Determine the server base URL for OpenAPI 2.0 or 3.x."""
    # OpenAPI 3.x
    servers = spec.get("servers")
    if isinstance(servers, list) and servers:
        url = servers[0].get("url", "") if isinstance(servers[0], dict) else ""
        if url:
            if url.startswith(("http://", "https://")):
                return url.rstrip("/")
            if source_url:  # relative server url -> resolve against source
                return urljoin(source_url, url).rstrip("/")
    # Swagger 2.0
    host = spec.get("host")
    if host:
        schemes = spec.get("schemes") or ["https"]
        base_path = spec.get("basePath", "") or ""
        return f"{schemes[0]}://{host}{base_path}".rstrip("/")
    # Fall back to the origin of the source URL.
    if source_url:
        parsed = urlparse(source_url)
        if parsed.scheme and parsed.netloc:
            return f"{parsed.scheme}://{parsed.netloc}"
    return ""


def _parse_security_schemes(spec: dict[str, Any], is_v3: bool) -> list[SecurityScheme]:
    schemes: list[SecurityScheme] = []
    if is_v3:
        defs = spec.get("components", {}).get("securitySchemes", {})
    else:
        defs = spec.get("securityDefinitions", {})
    for name, raw in (defs or {}).items():
        if not isinstance(raw, dict):
            continue
        schemes.append(
            SecurityScheme(
                name=name,
                type=raw.get("type", "unknown"),
                scheme=raw.get("scheme"),
                location=raw.get("in"),
                header_name=raw.get("name"),
                description=raw.get("description"),
            )
        )
    return schemes


def _make_operation_id(method: str, path: str, raw_op: dict[str, Any]) -> str:
    explicit = raw_op.get("operationId")
    if explicit:
        return str(explicit)
    slug = path.strip("/").replace("/", "_").replace("{", "").replace("}", "")
    slug = "".join(c if c.isalnum() or c == "_" else "_" for c in slug)
    return f"{method.lower()}_{slug or 'root'}"


def _parse_parameters(raw_params: Iterable[Any]) -> list[ParameterInfo]:
    params: list[ParameterInfo] = []
    for raw in raw_params:
        if not isinstance(raw, dict):
            continue
        loc = raw.get("in", "query")
        if loc not in ("path", "query", "header", "cookie"):
            continue
        # 3.x nests schema; 2.0 puts type info inline.
        schema = raw.get("schema")
        if not isinstance(schema, dict):
            schema = {k: raw[k] for k in ("type", "format", "enum", "items") if k in raw}
        params.append(
            ParameterInfo(
                name=raw.get("name", ""),
                location=loc,
                required=bool(raw.get("required", loc == "path")),
                description=raw.get("description"),
                schema=schema or {},
                example=raw.get("example"),
            )
        )
    return params


def _parse_request_body_v3(raw_op: dict[str, Any]) -> tuple[dict | None, bool, str | None]:
    body = raw_op.get("requestBody")
    if not isinstance(body, dict):
        return None, False, None
    content = body.get("content", {})
    if not isinstance(content, dict) or not content:
        return None, bool(body.get("required", False)), None
    # Prefer JSON; otherwise take the first declared content type.
    ctype = "application/json" if "application/json" in content else next(iter(content))
    media = content.get(ctype, {})
    schema = media.get("schema") if isinstance(media, dict) else None
    return schema, bool(body.get("required", False)), ctype


def _parse_request_body_v2(
    params: list[Any], consumes: list[str]
) -> tuple[dict | None, bool, str | None]:
    for raw in params:
        if isinstance(raw, dict) and raw.get("in") == "body":
            ctype = consumes[0] if consumes else "application/json"
            return raw.get("schema"), bool(raw.get("required", False)), ctype
    # form params -> synthesize an object schema
    form = [p for p in params if isinstance(p, dict) and p.get("in") == "formData"]
    if form:
        props = {p["name"]: {"type": p.get("type", "string")} for p in form if p.get("name")}
        required = [p["name"] for p in form if p.get("required") and p.get("name")]
        schema = {"type": "object", "properties": props}
        if required:
            schema["required"] = required
        ctype = consumes[0] if consumes else "application/x-www-form-urlencoded"
        return schema, bool(required), ctype
    return None, False, None


def parse_spec(spec: dict[str, Any], source_url: str | None = None) -> ParsedSpec:
    """Parse a raw spec document into a :class:`ParsedSpec`."""
    is_v3 = "openapi" in spec
    openapi_version = str(spec.get("openapi") or spec.get("swagger") or "unknown")
    info = spec.get("info", {}) if isinstance(spec.get("info"), dict) else {}

    resolver = _RefResolver(spec)
    base_url = _detect_base_url(spec, source_url)
    security_schemes = _parse_security_schemes(spec, is_v3)
    global_consumes = spec.get("consumes", []) if not is_v3 else []

    operations: list[Operation] = []
    seen_ids: set[str] = set()
    paths = spec.get("paths", {})
    if not isinstance(paths, dict):
        paths = {}

    for path, path_item in paths.items():
        if not isinstance(path_item, dict):
            continue
        # Parameters declared at the path level apply to all operations.
        shared_params = resolver.resolve(path_item.get("parameters", []))
        for method in HTTP_METHODS:
            raw_op = path_item.get(method)
            if not isinstance(raw_op, dict):
                continue
            raw_op = resolver.resolve(raw_op)

            op_params = list(shared_params) + list(raw_op.get("parameters", []) or [])
            parameters = _parse_parameters(op_params)

            if is_v3:
                body_schema, body_required, ctype = _parse_request_body_v3(raw_op)
            else:
                consumes = raw_op.get("consumes", global_consumes)
                body_schema, body_required, ctype = _parse_request_body_v2(op_params, consumes)

            op_id = _make_operation_id(method, path, raw_op)
            # Guarantee uniqueness even with duplicate operationIds.
            unique_id = op_id
            suffix = 2
            while unique_id in seen_ids:
                unique_id = f"{op_id}_{suffix}"
                suffix += 1
            seen_ids.add(unique_id)

            responses = {
                str(code): (r.get("description", "") if isinstance(r, dict) else "")
                for code, r in (raw_op.get("responses", {}) or {}).items()
            }

            operations.append(
                Operation(
                    operation_id=unique_id,
                    method=method.upper(),
                    path=path,
                    summary=raw_op.get("summary", "") or "",
                    description=raw_op.get("description", "") or "",
                    tags=[str(t) for t in (raw_op.get("tags") or [])],
                    parameters=parameters,
                    request_body_schema=body_schema,
                    request_body_required=body_required,
                    request_content_type=ctype,
                    responses=responses,
                )
            )

    return ParsedSpec(
        title=info.get("title", "Untitled API"),
        version=str(info.get("version", "")),
        openapi_version=openapi_version,
        base_url=base_url,
        operations=operations,
        security_schemes=security_schemes,
        raw=spec,
    )
