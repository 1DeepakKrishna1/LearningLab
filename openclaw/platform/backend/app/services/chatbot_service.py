"""AI Chatbot service — natural-language control plane.

Capabilities: NL workflow creation (via the AI builder), workflow execution,
status queries, tool discovery, agent listing, and basic debugging. Intent routing
is keyword-based with an LLM-free fallback so it works without credentials; workflow
creation itself uses the AI builder (LLM when available, heuristic otherwise).
"""
from __future__ import annotations

import re
from typing import Any

from ..ai_builder.generator import WorkflowGenerator
from .agent_service import AgentService
from .execution_service import ExecutionService
from .tool_service import ToolService
from .workflow_service import WorkflowService


class ChatbotService:
    def __init__(self, generator: WorkflowGenerator, workflows: WorkflowService,
                 executions: ExecutionService, tools: ToolService,
                 agents: AgentService) -> None:
        self._generator = generator
        self._workflows = workflows
        self._executions = executions
        self._tools = tools
        self._agents = agents

    async def chat(self, message: str, user_id: str | None = None) -> dict[str, Any]:
        text = message.strip()
        low = text.lower()

        if any(kw in low for kw in ("create", "build", "make", "design", "generate")) \
                and "workflow" in low:
            return await self._create_workflow(text, user_id)
        if low.startswith("run ") or "run workflow" in low or "execute" in low:
            return await self._run_workflow(text, user_id)
        if "status" in low:
            return await self._status(text)
        if "tool" in low and any(kw in low for kw in ("list", "what", "show", "discover", "find")):
            return self._list_tools(text)
        if "agent" in low and any(kw in low for kw in ("list", "what", "show")):
            return await self._list_agents()
        return self._help()

    # --- intents ---
    async def _create_workflow(self, text: str, user_id: str | None) -> dict[str, Any]:
        workflow = await self._generator.generate(text)
        workflow.created_by = user_id
        saved = await self._workflows.save(workflow)
        validation = WorkflowService.validate_obj(saved)
        status_note = ("valid" if validation["valid"]
                       else "a draft with issues: " + "; ".join(validation["errors"]))
        reply = (f"I created the workflow **{saved.name}** with {len(saved.nodes)} nodes. "
                 f"It is {status_note}. "
                 f"Open it in the Workflow Builder to review and run.")
        return {"reply": reply, "action": "workflow_created",
                "data": {"workflow_id": saved.id, "workflow": saved.model_dump(),
                         "validation": validation}}

    async def _run_workflow(self, text: str, user_id: str | None) -> dict[str, Any]:
        target = self._extract_workflow_ref(text)
        wf = await self._resolve_workflow(target)
        if not wf:
            return {"reply": f"I couldn't find a workflow matching '{target}'.",
                    "action": "error", "data": {}}
        execution = await self._executions.start(wf.id, trigger_type="manual",
                                                 created_by=user_id)
        return {"reply": f"Started **{wf.name}** (execution `{execution.id}`).",
                "action": "execution_started",
                "data": {"execution_id": execution.id, "workflow_id": wf.id}}

    async def _status(self, text: str) -> dict[str, Any]:
        ids = re.findall(r"[0-9a-f]{16,}", text)
        if ids:
            ex = await self._executions.get(ids[0])
            if ex:
                return {"reply": f"Execution `{ex.id}` is **{ex.status.value}** "
                                 f"({len(ex.node_runs)} nodes processed).",
                        "action": "status", "data": ex.model_dump()}
        recent = await self._executions.list()
        summary = ", ".join(f"{e.workflow_name}: {e.status.value}" for e in recent[:5]) or "none"
        return {"reply": f"Recent executions — {summary}.", "action": "status",
                "data": {"recent": [e.model_dump() for e in recent[:5]]}}

    def _list_tools(self, text: str) -> dict[str, Any]:
        query = None
        m = re.search(r"(?:for|about|matching)\s+([a-zA-Z ]+)", text)
        if m:
            query = m.group(1).strip()
        tools = self._tools.list(query)[:15]
        listing = "\n".join(f"- `{t.id}` — {t.display_name}" for t in tools)
        return {"reply": f"Found {len(tools)} tools:\n{listing}", "action": "tools",
                "data": {"tools": [t.model_dump() for t in tools]}}

    async def _list_agents(self) -> dict[str, Any]:
        agents = await self._agents.list()
        listing = "\n".join(f"- {a.name} ({a.role.value})" for a in agents) or "no agents yet"
        return {"reply": f"Configured agents:\n{listing}", "action": "agents",
                "data": {"agents": [a.model_dump() for a in agents]}}

    def _help(self) -> dict[str, Any]:
        return {"reply": (
            "I can help you build and run agentic workflows. Try:\n"
            "- *Create a workflow that reads email attachments and stores invoices*\n"
            "- *Run workflow <name>*\n"
            "- *Status*\n"
            "- *List tools for excel*\n"
            "- *List agents*"), "action": "help", "data": {}}

    # --- helpers ---
    @staticmethod
    def _extract_workflow_ref(text: str) -> str:
        m = re.search(r"(?:run|execute)\s+(?:workflow\s+)?(.+)", text, re.IGNORECASE)
        return m.group(1).strip(" .'\"") if m else text

    async def _resolve_workflow(self, ref: str):
        wf = await self._workflows.get(ref)
        if wf:
            return wf
        for w in await self._workflows.list():
            if w.name.lower() == ref.lower() or ref.lower() in w.name.lower():
                return w
        return None
