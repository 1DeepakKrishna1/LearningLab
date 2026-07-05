"""Agent CRUD service."""
from __future__ import annotations

from ..domain.agent import Agent, AgentCreate, AgentUpdate
from ..domain.common import iso
from ..storage.repository import Repository


class AgentService:
    def __init__(self, repo: Repository[Agent]) -> None:
        self._repo = repo

    async def list(self) -> list[Agent]:
        return await self._repo.list()

    async def get(self, agent_id: str) -> Agent | None:
        return await self._repo.get(agent_id)

    async def create(self, data: AgentCreate, created_by: str | None = None) -> Agent:
        agent = Agent(**data.model_dump(), created_by=created_by)
        return await self._repo.add(agent)

    async def update(self, agent_id: str, patch: AgentUpdate) -> Agent | None:
        agent = await self._repo.get(agent_id)
        if not agent:
            return None
        for key, value in patch.model_dump(exclude_unset=True).items():
            setattr(agent, key, value)
        agent.updated_at = iso()
        return await self._repo.update(agent)

    async def delete(self, agent_id: str) -> bool:
        return await self._repo.delete(agent_id)
