"""Tool registry domain models."""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from .common import iso


class ToolParameter(BaseModel):
    """A single input parameter parsed from a tool's README / introspection."""

    name: str
    type: str = "string"
    required: bool = False
    default: Any | None = None
    description: str = ""


class ToolReturn(BaseModel):
    """A documented field of a tool's return value."""

    field: str
    type: str = "string"
    description: str = ""


class ToolManifest(BaseModel):
    """Fully-resolved metadata for one discovered tool.

    `id` is the stable `<category>.<tool_folder>` identifier used everywhere
    (workflow node types, agent allow-lists, audit logs).
    """

    id: str
    name: str
    display_name: str
    category: str
    description: str = ""
    impl_path: str
    class_name: str | None = None
    parameters: list[ToolParameter] = Field(default_factory=list)
    returns: list[ToolReturn] = Field(default_factory=list)
    input_schema: dict[str, Any] = Field(default_factory=dict)
    examples: list[Any] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    icon: str = "wrench"
    color: str = "#6366F1"
    source: str = "readme"          # readme | introspection
    has_readme: bool = True
    discovered_at: str = Field(default_factory=iso)

    @property
    def node_type(self) -> str:
        """The workflow node type that maps to this tool."""
        return f"tool.{self.id}"
