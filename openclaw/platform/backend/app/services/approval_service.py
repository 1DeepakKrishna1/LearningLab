"""Human-in-the-loop approval service."""
from __future__ import annotations

from ..domain.approval import Approval, ApprovalDecision
from ..domain.common import iso
from ..domain.enums import ApprovalStatus
from ..logging_setup import get_logger
from ..storage.repository import Repository
from .execution_service import ExecutionService

logger = get_logger("service.approval")


class ApprovalService:
    def __init__(self, repo: Repository[Approval], executions: ExecutionService) -> None:
        self._repo = repo
        self._executions = executions

    async def list(self, status: str | None = None) -> list[Approval]:
        items = await self._repo.list()
        if status:
            items = [a for a in items if a.status.value == status]
        items.sort(key=lambda a: a.created_at, reverse=True)
        return items

    async def get(self, approval_id: str) -> Approval | None:
        return await self._repo.get(approval_id)

    async def decide(self, decision: ApprovalDecision, decided_by: str | None = None) -> Approval:
        approval = await self._repo.get(decision.approval_id)
        if not approval:
            raise KeyError("Approval not found.")
        if approval.status != ApprovalStatus.PENDING:
            raise ValueError(f"Approval already {approval.status.value}.")
        approval.status = decision.decision
        approval.comment = decision.comment
        approval.decided_by = decided_by
        approval.decided_at = iso()
        await self._repo.update(approval)
        logger.info("Approval %s -> %s", approval.id, approval.status.value)

        # Escalation keeps the run waiting; every other decision resumes it so the
        # approval node can read the outcome and route the branch.
        if approval.status != ApprovalStatus.ESCALATED:
            await self._executions.resume(approval.execution_id)
        return approval
