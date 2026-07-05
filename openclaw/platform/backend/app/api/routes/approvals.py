"""Human-in-the-loop approval routes."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from ...domain.approval import Approval, ApprovalDecision
from ..deps import ContainerDep, CurrentUser, require

router = APIRouter(tags=["approvals"])


@router.get("/approvals", response_model=list[Approval],
            dependencies=[Depends(require("approval:read"))])
async def list_approvals(container: ContainerDep, status: str | None = None) -> list[Approval]:
    return await container.approval_service.list(status)


@router.get("/approvals/{approval_id}", response_model=Approval,
            dependencies=[Depends(require("approval:read"))])
async def get_approval(approval_id: str, container: ContainerDep) -> Approval:
    approval = await container.approval_service.get(approval_id)
    if not approval:
        raise HTTPException(404, "Approval not found.")
    return approval


async def _respond(body: ApprovalDecision, container: ContainerDep, user: CurrentUser) -> Approval:
    try:
        return await container.approval_service.decide(body, decided_by=user.id)
    except KeyError as exc:
        raise HTTPException(404, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc


@router.post("/approvals/respond", response_model=Approval,
             dependencies=[Depends(require("approval:decide"))])
async def respond(body: ApprovalDecision, container: ContainerDep,
                  user: CurrentUser) -> Approval:
    return await _respond(body, container, user)


# spec alias
@router.post("/approval/respond", response_model=Approval,
             dependencies=[Depends(require("approval:decide"))])
async def respond_alias(body: ApprovalDecision, container: ContainerDep,
                        user: CurrentUser) -> Approval:
    return await _respond(body, container, user)
