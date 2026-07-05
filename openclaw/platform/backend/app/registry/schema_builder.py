"""Build a JSON Schema (and dynamic Pydantic model) from tool parameters."""
from __future__ import annotations

from typing import Any, Type

from pydantic import BaseModel, Field, create_model

from ..domain.tool import ToolParameter

# Map the loose type strings found in READMEs to JSON-schema types.
_TYPE_MAP = {
    "string": "string", "str": "string", "text": "string",
    "integer": "integer", "int": "integer",
    "number": "number", "float": "number", "double": "number",
    "boolean": "boolean", "bool": "boolean",
    "array": "array", "list": "array",
    "object": "object", "dict": "object", "json": "object",
}

_PY_TYPE = {
    "string": str, "integer": int, "number": float,
    "boolean": bool, "array": list, "object": dict,
}


def _json_type(raw: str) -> str:
    raw = (raw or "string").lower().strip()
    # "string or list" / "string|array" → take the first recognised token.
    for token in raw.replace("|", " ").replace("/", " ").replace(",", " ").split():
        if token in _TYPE_MAP:
            return _TYPE_MAP[token]
    return "string"


def build_input_schema(parameters: list[ToolParameter]) -> dict[str, Any]:
    """Return a JSON-Schema ``object`` describing the tool's inputs."""
    props: dict[str, Any] = {}
    required: list[str] = []
    for p in parameters:
        entry: dict[str, Any] = {
            "type": _json_type(p.type),
            "description": p.description or p.name,
        }
        if p.default is not None:
            entry["default"] = p.default
        props[p.name] = entry
        if p.required:
            required.append(p.name)
    schema: dict[str, Any] = {"type": "object", "properties": props}
    if required:
        schema["required"] = required
    return schema


def build_args_model(tool_id: str, parameters: list[ToolParameter]) -> Type[BaseModel]:
    """Create a dynamic Pydantic model for a tool's args (used by LangChain tools)."""
    fields: dict[str, Any] = {}
    for p in parameters:
        py = _PY_TYPE.get(_json_type(p.type), str)
        if p.required:
            fields[p.name] = (py, Field(description=p.description or p.name))
        else:
            default = p.default if p.default is not None else None
            fields[p.name] = (py | None, Field(default=default, description=p.description or p.name))
    safe = tool_id.replace(".", "_").replace("-", "_")
    return create_model(f"Args_{safe}", **fields)  # type: ignore[call-overload]
