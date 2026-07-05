"""Workflow routes (RESTful + the spec's POST /workflow/* aliases)."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from ...domain.workflow import Workflow, WorkflowCreate, WorkflowUpdate
from ..deps import ContainerDep, CurrentUser, require

router = APIRouter(tags=["workflows"])


class RunRequest(BaseModel):
    trigger_type: str = "manual"
    payload: dict[str, Any] = {}
    variables: dict[str, Any] = {}


class GenerateRequest(BaseModel):
    prompt: str


# --- RESTful collection ---
@router.get("/workflows", response_model=list[Workflow],
            dependencies=[Depends(require("workflow:read"))])
async def list_workflows(container: ContainerDep) -> list[Workflow]:
    return await container.workflow_service.list()


@router.post("/workflows", response_model=Workflow,
             dependencies=[Depends(require("workflow:write"))])
async def create_workflow(body: WorkflowCreate, container: ContainerDep,
                          user: CurrentUser) -> Workflow:
    return await container.workflow_service.create(body, created_by=user.id)


@router.get("/workflows/{workflow_id}", response_model=Workflow,
            dependencies=[Depends(require("workflow:read"))])
async def get_workflow(workflow_id: str, container: ContainerDep) -> Workflow:
    wf = await container.workflow_service.get(workflow_id)
    if not wf:
        raise HTTPException(404, "Workflow not found.")
    return wf


@router.put("/workflows/{workflow_id}", response_model=Workflow,
            dependencies=[Depends(require("workflow:write"))])
async def update_workflow(workflow_id: str, body: WorkflowUpdate,
                          container: ContainerDep) -> Workflow:
    wf = await container.workflow_service.update(workflow_id, body)
    if not wf:
        raise HTTPException(404, "Workflow not found.")
    return wf


@router.delete("/workflows/{workflow_id}",
               dependencies=[Depends(require("workflow:delete"))])
async def delete_workflow(workflow_id: str, container: ContainerDep) -> dict:
    return {"deleted": await container.workflow_service.delete(workflow_id)}


@router.get("/workflows/{workflow_id}/validate",
            dependencies=[Depends(require("workflow:read"))])
async def validate_workflow(workflow_id: str, container: ContainerDep) -> dict:
    return await container.workflow_service.validate(workflow_id)


@router.post("/workflows/{workflow_id}/run",
             dependencies=[Depends(require("workflow:run"))])
async def run_workflow(workflow_id: str, body: RunRequest, container: ContainerDep,
                       user: CurrentUser) -> dict:
    try:
        execution = await container.execution_service.start(
            workflow_id, body.trigger_type, body.payload, body.variables, user.id)
    except KeyError as exc:
        raise HTTPException(404, str(exc)) from exc
    return {"execution_id": execution.id, "status": execution.status.value}


@router.post("/workflows/generate", response_model=Workflow,
             dependencies=[Depends(require("workflow:write"))])
async def generate_workflow(body: GenerateRequest, container: ContainerDep,
                            user: CurrentUser) -> Workflow:
    wf = await container.generator.generate(body.prompt)
    wf.created_by = user.id
    return await container.workflow_service.save(wf)


# --- spec aliases ---
@router.post("/workflow/create", response_model=Workflow,
             dependencies=[Depends(require("workflow:write"))])
async def create_workflow_alias(body: WorkflowCreate, container: ContainerDep,
                                user: CurrentUser) -> Workflow:
    return await container.workflow_service.create(body, created_by=user.id)


@router.post("/workflow/run", dependencies=[Depends(require("workflow:run"))])
async def run_workflow_alias(workflow_id: str, container: ContainerDep,
                             user: CurrentUser, body: RunRequest | None = None) -> dict:
    body = body or RunRequest()
    execution = await container.execution_service.start(
        workflow_id, body.trigger_type, body.payload, body.variables, user.id)
    return {"execution_id": execution.id, "status": execution.status.value}


@router.get("/workflow/status/{execution_id}",
            dependencies=[Depends(require("execution:read"))])
async def workflow_status_alias(execution_id: str, container: ContainerDep) -> dict:
    ex = await container.execution_service.get(execution_id)
    if not ex:
        raise HTTPException(404, "Execution not found.")
    return {"execution_id": ex.id, "status": ex.status.value,
            "workflow": ex.workflow_name, "node_runs": len(ex.node_runs)}
