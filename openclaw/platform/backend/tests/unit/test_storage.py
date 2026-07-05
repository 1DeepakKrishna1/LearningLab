"""Unit tests for the JSON repository."""
import pytest

from app.domain.agent import Agent
from app.storage.json_repository import JsonRepository


@pytest.fixture
def repo(tmp_path):
    return JsonRepository(tmp_path / "agents.json", Agent)


async def test_add_get_update_delete(repo):
    agent = Agent(name="A")
    await repo.add(agent)
    assert (await repo.get(agent.id)).name == "A"

    agent.name = "B"
    await repo.update(agent)
    assert (await repo.get(agent.id)).name == "B"

    assert await repo.count() == 1
    assert await repo.delete(agent.id) is True
    assert await repo.get(agent.id) is None


async def test_add_duplicate_raises(repo):
    agent = Agent(name="A")
    await repo.add(agent)
    with pytest.raises(KeyError):
        await repo.add(agent)


async def test_persistence_across_instances(repo, tmp_path):
    agent = Agent(name="Persist")
    await repo.add(agent)
    fresh = JsonRepository(tmp_path / "agents.json", Agent)
    loaded = await fresh.get(agent.id)
    assert loaded is not None and loaded.name == "Persist"


async def test_find_predicate(repo):
    await repo.add(Agent(name="alpha"))
    await repo.add(Agent(name="beta"))
    found = await repo.find(lambda a: a.name.startswith("al"))
    assert len(found) == 1 and found[0].name == "alpha"
