"""Execution monitoring routes."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from ...domain.execution import Execution
from ..deps import ContainerDep, require

router = APIRouter(tags=["executions"])


@router.get("/executions", response_model=list[Execution],
            dependencies=[Depends(require("execution:read"))])
async def list_executions(container: ContainerDep, workflow_id: str | None = None,
                          status: str | None = None) -> list[Execution]:
    return await container.execution_service.list(workflow_id, status)


@router.get("/executions/{execution_id}", response_model=Execution,
            dependencies=[Depends(require("execution:read"))])
async def get_execution(execution_id: str, container: ContainerDep) -> Execution:
    ex = await container.execution_service.get(execution_id)
    if not ex:
        raise HTTPException(404, "Execution not found.")
    return ex


@router.post("/executions/{execution_id}/cancel",
             dependencies=[Depends(require("execution:cancel"))])
async def cancel_execution(execution_id: str, container: ContainerDep) -> dict:
    ex = await container.execution_service.cancel(execution_id)
    if not ex:
        raise HTTPException(404, "Execution not found.")
    return {"execution_id": ex.id, "status": ex.status.value}


@router.post("/executions/{execution_id}/resume",
             dependencies=[Depends(require("execution:cancel"))])
async def resume_execution(execution_id: str, container: ContainerDep) -> dict:
    ex = await container.execution_service.resume(execution_id)
    if not ex:
        raise HTTPException(404, "Execution not found.")
    return {"execution_id": ex.id, "status": ex.status.value}
