"""Workflow graph domain models — React-Flow compatible."""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from .common import iso, new_id
from .enums import WorkflowStatus


class NodePosition(BaseModel):
    x: float = 0
    y: float = 0


class NodeData(BaseModel):
    """The mutable payload carried by every node (free-form `config`)."""

    label: str = ""
    config: dict[str, Any] = Field(default_factory=dict)
    # Optional references used by specific node groups:
    agent_id: str | None = None        # agent.* nodes
    tool_id: str | None = None         # tool.* nodes (redundant with type, but explicit)

    model_config = {"extra": "allow"}


class WorkflowNode(BaseModel):
    """A React-Flow node. `type` follows the taxonomy: <group>.<name>."""

    id: str
    type: str
    position: NodePosition = Field(default_factory=NodePosition)
    data: NodeData = Field(default_factory=NodeData)

    @property
    def group(self) -> str:
        return self.type.split(".", 1)[0]


class WorkflowEdge(BaseModel):
    """A React-Flow edge. `sourceHandle` carries branch labels (e.g. 'true'/'approved')."""

    id: str = Field(default_factory=lambda: f"e_{new_id()[:8]}")
    source: str
    target: str
    sourceHandle: str | None = None
    targetHandle: str | None = None
    label: str | None = None


class Workflow(BaseModel):
    """A complete workflow definition (persisted in workflows.json)."""

    id: str = Field(default_factory=new_id)
    name: str
    description: str = ""
    version: int = 1
    status: WorkflowStatus = WorkflowStatus.DRAFT
    nodes: list[WorkflowNode] = Field(default_factory=list)
    edges: list[WorkflowEdge] = Field(default_factory=list)
    variables: dict[str, Any] = Field(default_factory=dict)
    tags: list[str] = Field(default_factory=list)
    created_by: str | None = None
    created_at: str = Field(default_factory=iso)
    updated_at: str = Field(default_factory=iso)

    # --- graph helpers ---
    def node(self, node_id: str) -> WorkflowNode | None:
        return next((n for n in self.nodes if n.id == node_id), None)

    def outgoing(self, node_id: str) -> list[WorkflowEdge]:
        return [e for e in self.edges if e.source == node_id]

    def incoming(self, node_id: str) -> list[WorkflowEdge]:
        return [e for e in self.edges if e.target == node_id]

    def trigger_nodes(self) -> list[WorkflowNode]:
        return [n for n in self.nodes if n.group == "trigger"]


class WorkflowCreate(BaseModel):
    name: str
    description: str = ""
    nodes: list[WorkflowNode] = Field(default_factory=list)
    edges: list[WorkflowEdge] = Field(default_factory=list)
    variables: dict[str, Any] = Field(default_factory=dict)
    tags: list[str] = Field(default_factory=list)


class WorkflowUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    status: WorkflowStatus | None = None
    nodes: list[WorkflowNode] | None = None
    edges: list[WorkflowEdge] | None = None
    variables: dict[str, Any] | None = None
    tags: list[str] | None = None
