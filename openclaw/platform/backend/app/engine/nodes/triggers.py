"""Trigger node handlers.

All trigger types share one behaviour at execution time: emit the trigger payload
as their output so downstream nodes can read ``{{ trigger.payload.* }}``. The
distinction between HTTP / Cron / Email / WhatsApp / etc. lives in *how the run is
started* (the API/scheduler/webhook layer), not in execution.
"""
from __future__ import annotations

from ...domain.execution import Execution
from ...domain.workflow import WorkflowNode
from ..context import ExecutionContext
from ..services import EngineServices
from .base import NodeResult, register_handler


class TriggerHandler:
    async def execute(self, node: WorkflowNode, ctx: ExecutionContext,
                      services: EngineServices, execution: Execution) -> NodeResult:
        payload = ctx.trigger.get("payload", {})
        return NodeResult.ok({
            "trigger_type": node.type,
            "payload": payload,
            **(payload if isinstance(payload, dict) else {}),
        })


register_handler("trigger", TriggerHandler())
