"""Agent domain models."""
from __future__ import annotations

from pydantic import BaseModel, Field

from .common import iso, new_id
from .enums import AgentCapability, AgentRole


class AgentLimits(BaseModel):
    """Per-agent security & resource guardrails."""

    max_iterations: int = 12
    timeout_seconds: int = 300
    # When set, the agent may ONLY call tools whose id is in this list.
    # Empty list => inherit the agent's `tools` field as the allow-list.
    tool_allow_list: list[str] = Field(default_factory=list)
    sandboxed: bool = False


class Agent(BaseModel):
    """An OpenClaw agent definition (persisted in agents.json)."""

    agent_id: str = Field(default_factory=new_id)
    name: str
    description: str = ""
    role: AgentRole = AgentRole.EXECUTOR
    type: str = "openclaw"
    tools: list[str] = Field(default_factory=list)      # tool manifest ids
    model: str | None = None
    provider: str | None = None
    temperature: float = 0.0
    system_prompt: str | None = None
    capabilities: list[AgentCapability] = Field(
        default_factory=lambda: [AgentCapability.TOOL_CALLING]
    )
    limits: AgentLimits = Field(default_factory=AgentLimits)
    created_by: str | None = None
    created_at: str = Field(default_factory=iso)
    updated_at: str = Field(default_factory=iso)

    @property
    def id(self) -> str:  # storage Repository expects `.id`
        return self.agent_id


class AgentCreate(BaseModel):
    name: str
    description: str = ""
    role: AgentRole = AgentRole.EXECUTOR
    tools: list[str] = Field(default_factory=list)
    model: str | None = None
    provider: str | None = None
    temperature: float = 0.0
    system_prompt: str | None = None
    capabilities: list[AgentCapability] = Field(
        default_factory=lambda: [AgentCapability.TOOL_CALLING]
    )
    limits: AgentLimits = Field(default_factory=AgentLimits)


class AgentUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    role: AgentRole | None = None
    tools: list[str] | None = None
    model: str | None = None
    provider: str | None = None
    temperature: float | None = None
    system_prompt: str | None = None
    capabilities: list[AgentCapability] | None = None
    limits: AgentLimits | None = None
