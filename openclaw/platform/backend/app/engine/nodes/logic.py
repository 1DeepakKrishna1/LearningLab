"""Logic node handlers: if_else, switch, parallel, merge, loop, wait, approval."""
from __future__ import annotations

import asyncio
from typing import Any

from ...domain.approval import Approval
from ...domain.enums import ApprovalChannel
from ...domain.execution import Execution
from ...domain.workflow import WorkflowNode
from ..context import ExecutionContext
from ..services import EngineServices
from .base import NodeResult, register_handler

# Cap an inline wait; longer waits suspend the run instead of blocking a worker.
_MAX_INLINE_WAIT = 5.0


def _coerce(value: Any) -> Any:
    if isinstance(value, str):
        low = value.strip().lower()
        if low in {"true", "false"}:
            return low == "true"
        try:
            return int(value)
        except ValueError:
            try:
                return float(value)
            except ValueError:
                return value
    return value


def evaluate_condition(left: Any, operator: str, right: Any) -> bool:
    left, right = _coerce(left), _coerce(right)
    op = (operator or "==").strip()
    try:
        if op in ("==", "eq"):
            return left == right
        if op in ("!=", "ne"):
            return left != right
        if op in (">", "gt"):
            return left > right
        if op in ("<", "lt"):
            return left < right
        if op in (">=", "gte"):
            return left >= right
        if op in ("<=", "lte"):
            return left <= right
        if op == "contains":
            return right in (left or "")
        if op == "not_contains":
            return right not in (left or "")
        if op == "exists":
            return left not in (None, "", [], {})
        if op == "empty":
            return left in (None, "", [], {})
    except TypeError:
        return False
    return False


class IfElseHandler:
    async def execute(self, node: WorkflowNode, ctx: ExecutionContext,
                      services: EngineServices, execution: Execution) -> NodeResult:
        cfg = ctx.interpolate(dict(node.data.config or {}))
        result = evaluate_condition(cfg.get("left"), cfg.get("operator", "=="), cfg.get("right"))
        branch = "true" if result else "false"
        return NodeResult.ok({"result": result, "branch": branch}, control=branch)


class SwitchHandler:
    async def execute(self, node: WorkflowNode, ctx: ExecutionContext,
                      services: EngineServices, execution: Execution) -> NodeResult:
        cfg = ctx.interpolate(dict(node.data.config or {}))
        value = _coerce(cfg.get("value"))
        cases = [str(_coerce(c)) for c in cfg.get("cases", [])]
        match = str(value) if str(value) in cases else "default"
        return NodeResult.ok({"value": value, "case": match}, control=match)


class ParallelHandler:
    """Pass-through fan-out. The executor runs all outgoing branches concurrently."""
    async def execute(self, node: WorkflowNode, ctx: ExecutionContext,
                      services: EngineServices, execution: Execution) -> NodeResult:
        return NodeResult.ok({"fanout": True})


class MergeHandler:
    """Collect all upstream node outputs into a single list."""
    async def execute(self, node: WorkflowNode, ctx: ExecutionContext,
                      services: EngineServices, execution: Execution) -> NodeResult:
        # The executor gates this node until all incoming edges resolve, and injects
        # the list of predecessor node ids as config["_sources"].
        sources = (node.data.config or {}).get("_sources", [])
        merged = [ctx.node_outputs.get(s) for s in sources]
        return NodeResult.ok({"merged": merged, "sources": sources})


class LoopHandler:
    """Iterate over an items list, recording the collection for downstream nodes.

    Full sub-graph looping (back-edges) is intentionally out of scope for the JSON
    engine; this provides item iteration semantics that cover the common cases.
    """
    async def execute(self, node: WorkflowNode, ctx: ExecutionContext,
                      services: EngineServices, execution: Execution) -> NodeResult:
        cfg = ctx.interpolate(dict(node.data.config or {}))
        items = cfg.get("items", [])
        if not isinstance(items, list):
            items = [items]
        return NodeResult.ok({"items": items, "count": len(items)})


class WaitHandler:
    async def execute(self, node: WorkflowNode, ctx: ExecutionContext,
                      services: EngineServices, execution: Execution) -> NodeResult:
        cfg = ctx.interpolate(dict(node.data.config or {}))
        seconds = float(cfg.get("seconds", 0) or 0)
        if seconds <= _MAX_INLINE_WAIT:
            if seconds > 0:
                await asyncio.sleep(seconds)
            return NodeResult.ok({"waited": seconds})
        # Long wait → suspend; resumed by the scheduler when the timer elapses.
        return NodeResult.waiting({"reason": "timer", "resume_after_seconds": seconds})


class ApprovalHandler:
    async def execute(self, node: WorkflowNode, ctx: ExecutionContext,
                      services: EngineServices, execution: Execution) -> NodeResult:
        cfg = ctx.interpolate(dict(node.data.config or {}))

        # If an approval for this node already exists, evaluate its decision.
        existing = await services.approval_repo.find(
            lambda a: a.execution_id == execution.id and a.node_id == node.id)
        if existing:
            decision = existing[-1]
            from ...domain.enums import ApprovalStatus
            if decision.status == ApprovalStatus.APPROVED:
                return NodeResult.ok({"approved": True, "by": decision.decided_by},
                                     control="approved")
            if decision.status == ApprovalStatus.REJECTED:
                return NodeResult.ok({"approved": False, "by": decision.decided_by},
                                     control="rejected")
            if decision.status == ApprovalStatus.CHANGES_REQUESTED:
                return NodeResult.ok({"changes_requested": True}, control="changes")
            # escalated / still pending → keep waiting
            return NodeResult.waiting({"reason": "approval", "approval_id": decision.id})

        # First visit → raise an approval request and suspend.
        channel = ApprovalChannel(cfg.get("channel", "ui"))
        approval = Approval(
            execution_id=execution.id,
            workflow_id=execution.workflow_id,
            node_id=node.id,
            title=cfg.get("title", node.data.label or "Approval required"),
            description=cfg.get("description", ""),
            channel=channel,
            approvers=cfg.get("approvers", []),
            payload={"context": ctx.snapshot()},
        )
        await services.approval_repo.add(approval)
        await services.emit_event("approval.requested",
                                  {"execution_id": execution.id, "approval_id": approval.id,
                                   "node_id": node.id})
        await services.write_audit(actor="system", action="approval_requested",
                                   result="info", execution_id=execution.id,
                                   detail={"approval_id": approval.id, "channel": channel.value})
        # Notify via messaging for email/whatsapp channels.
        if channel in (ApprovalChannel.WHATSAPP, ApprovalChannel.EMAIL) and services.messaging:
            for approver in approval.approvers:
                await services.messaging.send(
                    approver,
                    f"Approval required: {approval.title}\n{approval.description}\n"
                    f"Reply APPROVE {approval.id} or REJECT {approval.id}.")
        return NodeResult.waiting({"reason": "approval", "approval_id": approval.id})


register_handler("logic.if_else", IfElseHandler())
register_handler("logic.switch", SwitchHandler())
register_handler("logic.parallel", ParallelHandler())
register_handler("logic.merge", MergeHandler())
register_handler("logic.loop", LoopHandler())
register_handler("logic.wait", WaitHandler())
register_handler("logic.approval", ApprovalHandler())
