"""Execution domain models."""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from .common import iso, new_id
from .enums import ExecutionStatus, NodeRunStatus


class TriggerInfo(BaseModel):
    type: str = "manual"
    payload: dict[str, Any] = Field(default_factory=dict)


class NodeRun(BaseModel):
    """The record of one node's execution within a run."""

    node_id: str
    node_type: str
    label: str = ""
    status: NodeRunStatus = NodeRunStatus.PENDING
    attempts: int = 0
    started_at: str | None = None
    finished_at: str | None = None
    output: dict[str, Any] | None = None
    error: str | None = None
    logs: list[str] = Field(default_factory=list)


class Checkpoint(BaseModel):
    """Minimal state needed to resume a suspended execution."""

    completed_nodes: list[str] = Field(default_factory=list)
    skipped_nodes: list[str] = Field(default_factory=list)
    node_outputs: dict[str, Any] = Field(default_factory=dict)
    controls: dict[str, str] = Field(default_factory=dict)  # node_id -> branch key taken
    pending_node: str | None = None        # node awaiting approval / wait


class Execution(BaseModel):
    """A single run of a workflow (persisted in executions.json)."""

    id: str = Field(default_factory=new_id)
    workflow_id: str
    workflow_version: int = 1
    workflow_name: str = ""
    status: ExecutionStatus = ExecutionStatus.PENDING
    trigger: TriggerInfo = Field(default_factory=TriggerInfo)
    variables: dict[str, Any] = Field(default_factory=dict)
    node_runs: list[NodeRun] = Field(default_factory=list)
    checkpoint: Checkpoint = Field(default_factory=Checkpoint)
    result: dict[str, Any] | None = None
    error: str | None = None
    created_by: str | None = None
    started_at: str | None = None
    finished_at: str | None = None
    created_at: str = Field(default_factory=iso)
    updated_at: str = Field(default_factory=iso)

    def node_run(self, node_id: str) -> NodeRun | None:
        return next((r for r in self.node_runs if r.node_id == node_id), None)

    def touch(self) -> None:
        self.updated_at = iso()
