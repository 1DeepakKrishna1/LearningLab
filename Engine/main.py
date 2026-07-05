"""Workflow Execution Engine – FastAPI application.

Endpoints
---------
GET  /                              Health-check
GET  /library                       List all registered agents and tools
GET  /workflows                     List available workflows
GET  /workflows/{name_or_id}        Get a workflow definition
POST /execute                       Execute a workflow (returns full execution state)
GET  /executions/{execution_id}     Retrieve a past execution by ID
GET  /executions                    List all execution summaries

Usage
-----
    uvicorn main:app --reload --host 0.0.0.0 --port 8000
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

load_dotenv()

# ── Engine & registry ────────────────────────────────────────────────────────
from core.engine import WorkflowEngine
from core.registry import Registry, load_all
from core.state import get_execution_summary

load_all()
_engine = WorkflowEngine()

# ── In-memory execution store ────────────────────────────────────────────────
_executions: Dict[str, Dict[str, Any]] = {}

# ── FastAPI app ───────────────────────────────────────────────────────────────
app = FastAPI(
    title="Workflow Execution Engine",
    description=(
        "Executes agent-based workflows defined in myworkflow.json. "
        "Supports topological-sort and LangGraph execution modes."
    ),
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request / Response models ─────────────────────────────────────────────────

class ExecuteRequest(BaseModel):
    workflow_name: str = Field(
        ...,
        description="Name or ID of the workflow to execute (from myworkflow.json).",
        examples=["Customer Onboarding (Myflow)"],
    )
    start_properties: Dict[str, Any] = Field(
        default_factory=dict,
        description="Input properties injected into the Start node (workflow input).",
        examples=[{"customer_id": "C001", "environment": "production"}],
    )


class ExecuteResponse(BaseModel):
    execution_id: str
    workflow_id: str
    workflow_name: str
    status: str
    started_at: Optional[str]
    completed_at: Optional[str]
    start_properties: Dict[str, Any]
    end_properties: Dict[str, Any]
    execution_log: List[Dict[str, Any]]
    node_records: Dict[str, Any]
    error: Optional[str]


# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/", tags=["Health"])
def health_check() -> Dict[str, Any]:
    return {
        "status": "ok",
        "service": "Workflow Execution Engine",
        "version": "1.0.0",
        "execution_mode": os.getenv("EXECUTION_MODE", "topological"),
        "registered_agents": len(Registry.list_agents()),
        "registered_tools": len(Registry.list_tools()),
    }


@app.get("/library", tags=["Library"])
def get_library() -> Dict[str, Any]:
    """Return all registered agents and tools."""
    return {
        "agents": [
            {
                "agent_id": aid,
                "name": Registry.get_agent(aid).name(),
                "description": Registry.get_agent(aid).description(),
            }
            for aid in sorted(Registry.list_agents())
        ],
        "tools": [
            {
                "tool_id": tid,
                "name": Registry.get_tool(tid).name(),
                "description": Registry.get_tool(tid).description(),
            }
            for tid in sorted(Registry.list_tools())
        ],
    }


@app.get("/workflows", tags=["Workflows"])
def list_workflows() -> List[Dict[str, Any]]:
    """List all available workflows."""
    return _engine.list_workflows()


@app.get("/workflows/{name_or_id}", tags=["Workflows"])
def get_workflow(name_or_id: str) -> Dict[str, Any]:
    """Retrieve a workflow definition by name or ID."""
    wf = _engine.get_workflow(name_or_id)
    if wf is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow '{name_or_id}' not found.",
        )
    return wf


@app.post(
    "/execute",
    response_model=ExecuteResponse,
    status_code=status.HTTP_200_OK,
    tags=["Execution"],
)
def execute_workflow(request: ExecuteRequest) -> ExecuteResponse:
    """Execute a workflow.

    * **workflow_name** – name or ID matching an entry in ``myworkflow.json``
    * **start_properties** – key/value pairs injected as workflow input

    Returns the complete execution state including per-node records,
    execution log, and the final ``end_properties`` (workflow output).
    """
    try:
        state = _engine.execute(
            workflow_name_or_id=request.workflow_name,
            start_properties=request.start_properties,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except Exception as exc:  # pylint: disable=broad-except
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        )

    # Persist for later retrieval
    _executions[state["execution_id"]] = state

    return ExecuteResponse(
        execution_id=state["execution_id"],
        workflow_id=state["workflow_id"],
        workflow_name=state["workflow_name"],
        status=state["status"],
        started_at=state.get("started_at"),
        completed_at=state.get("completed_at"),
        start_properties=state["start_properties"],
        end_properties=state.get("end_properties", {}),
        execution_log=state.get("execution_log", []),
        node_records=state.get("node_records", {}),
        error=state.get("error"),
    )


@app.get("/executions", tags=["Execution"])
def list_executions() -> List[Dict[str, Any]]:
    """List summaries of all past executions (in-memory, resets on restart)."""
    return [get_execution_summary(s) for s in _executions.values()]


@app.get("/executions/{execution_id}", tags=["Execution"])
def get_execution(execution_id: str) -> Dict[str, Any]:
    """Retrieve the full state of a past execution."""
    state = _executions.get(execution_id)
    if state is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Execution '{execution_id}' not found.",
        )
    return state


# ── Entry point ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=os.getenv("API_HOST", "0.0.0.0"),
        port=int(os.getenv("API_PORT", "8000")),
        reload=os.getenv("API_RELOAD", "true").lower() == "true",
    )
