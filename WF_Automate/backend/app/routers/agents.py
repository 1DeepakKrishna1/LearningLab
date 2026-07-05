from fastapi import APIRouter
from typing import List, Dict, Any

router = APIRouter()

_agents = [
    {"id": 1, "name": "Agent A", "tools": ["tool1", "tool2"]},
    {"id": 2, "name": "Agent B", "tools": ["tool3"]},
]

@router.get("/", response_model=List[Dict[str, Any]])
def list_agents():
    return _agents

@router.get("/{agent_id}")
def get_agent(agent_id: int):
    for ag in _agents:
        if ag["id"] == agent_id:
            return ag
    return {"error": "Not found"}
