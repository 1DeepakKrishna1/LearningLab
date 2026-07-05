"""Agent management routes (RESTful + spec's /agent/* aliases)."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from ...domain.agent import Agent, AgentCreate, AgentUpdate
from ..deps import ContainerDep, CurrentUser, require

router = APIRouter(tags=["agents"])


class RunAgentRequest(BaseModel):
    task: str
    context: dict[str, Any] = {}


@router.get("/agents", response_model=list[Agent],
            dependencies=[Depends(require("agent:read"))])
async def list_agents(container: ContainerDep) -> list[Agent]:
    return await container.agent_service.list()


@router.post("/agents", response_model=Agent,
             dependencies=[Depends(require("agent:write"))])
async def create_agent(body: AgentCreate, container: ContainerDep,
                       user: CurrentUser) -> Agent:
    return await container.agent_service.create(body, created_by=user.id)


@router.get("/agents/{agent_id}", response_model=Agent,
            dependencies=[Depends(require("agent:read"))])
async def get_agent(agent_id: str, container: ContainerDep) -> Agent:
    agent = await container.agent_service.get(agent_id)
    if not agent:
        raise HTTPException(404, "Agent not found.")
    return agent


@router.put("/agents/{agent_id}", response_model=Agent,
            dependencies=[Depends(require("agent:write"))])
async def update_agent(agent_id: str, body: AgentUpdate, container: ContainerDep) -> Agent:
    agent = await container.agent_service.update(agent_id, body)
    if not agent:
        raise HTTPException(404, "Agent not found.")
    return agent


@router.delete("/agents/{agent_id}", dependencies=[Depends(require("agent:delete"))])
async def delete_agent(agent_id: str, container: ContainerDep) -> dict:
    return {"deleted": await container.agent_service.delete(agent_id)}


@router.post("/agents/{agent_id}/run", dependencies=[Depends(require("tool:execute"))])
async def run_agent(agent_id: str, body: RunAgentRequest, container: ContainerDep) -> dict:
    agent = await container.agent_service.get(agent_id)
    if not agent:
        raise HTTPException(404, "Agent not found.")
    return await container.agent_runtime.run(agent, body.task, body.context)


# --- spec aliases ---
@router.get("/agent/list", response_model=list[Agent],
            dependencies=[Depends(require("agent:read"))])
async def agent_list_alias(container: ContainerDep) -> list[Agent]:
    return await container.agent_service.list()


@router.post("/agent/create", response_model=Agent,
             dependencies=[Depends(require("agent:write"))])
async def agent_create_alias(body: AgentCreate, container: ContainerDep,
                             user: CurrentUser) -> Agent:
    return await container.agent_service.create(body, created_by=user.id)
