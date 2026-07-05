"""Tool registry routes."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from ...domain.tool import ToolManifest
from ..deps import ContainerDep, require

router = APIRouter(tags=["tools"])


class ExecuteToolRequest(BaseModel):
    tool_id: str
    inputs: dict[str, Any] = {}


@router.get("/tools", response_model=list[ToolManifest],
            dependencies=[Depends(require("tool:read"))])
async def list_tools(container: ContainerDep, q: str | None = None) -> list[ToolManifest]:
    return container.tool_service.list(q)


@router.get("/tools/catalog/nodes", dependencies=[Depends(require("tool:read"))])
async def node_catalog(container: ContainerDep) -> dict:
    """Full node palette for the workflow builder (static groups + tool nodes)."""
    return container.tool_service.node_catalog()


@router.post("/tools/refresh", dependencies=[Depends(require("tool:refresh"))])
async def refresh_tools(container: ContainerDep) -> dict:
    return await container.tool_service.refresh()


@router.post("/tools/execute", dependencies=[Depends(require("tool:execute"))])
async def execute_tool(body: ExecuteToolRequest, container: ContainerDep) -> dict:
    if container.tool_service.get(body.tool_id) is None:
        raise HTTPException(404, f"Tool '{body.tool_id}' not found.")
    result = await container.tool_service.execute(body.tool_id, body.inputs)
    await container.audit_service.log(action="tool_call", actor="user",
                                      result=result.get("status", "success"),
                                      detail={"tool": body.tool_id})
    return result


@router.get("/tools/{tool_id:path}", response_model=ToolManifest,
            dependencies=[Depends(require("tool:read"))])
async def get_tool(tool_id: str, container: ContainerDep) -> ToolManifest:
    tool = container.tool_service.get(tool_id)
    if not tool:
        raise HTTPException(404, "Tool not found.")
    return tool
