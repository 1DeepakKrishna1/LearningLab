"""Generate a workflow from a natural-language description.

Pipeline (mirrors the spec's 5 steps):
  1. Understand intent          → LLM reads the brief
  2. Discover suitable tools    → registry search seeds a candidate catalog
  3. Create workflow graph      → LLM emits nodes + edges using the node taxonomy
  4. Generate workflow JSON     → validated into a Workflow model
  5. Render in UI               → returned to the client (React Flow consumes it)

Degrades to a deterministic heuristic builder when no LLM is configured, so the
endpoint always returns a usable draft.
"""
from __future__ import annotations

import json
import re
from typing import Any

from ..config import Settings
from ..domain.workflow import Workflow, WorkflowEdge, WorkflowNode
from ..logging_setup import get_logger
from ..registry.tool_registry import ToolRegistry

logger = get_logger("ai_builder")

_TAXONOMY = """
Node types you may use:
  trigger.manual | trigger.http | trigger.cron | trigger.webhook | trigger.email |
  trigger.whatsapp | trigger.file_upload | trigger.google_sheet_row
  agent.openclaw | agent.supervisor | agent.planner | agent.research |
  agent.executor | agent.reviewer
  logic.if_else | logic.switch | logic.parallel | logic.merge | logic.loop |
  logic.wait | logic.approval
  action.send_email | action.send_whatsapp | action.api_call | action.file_write |
  action.generate_report
  tool.<tool_id>   (use exact tool ids from the provided catalog)
""".strip()


def _keywords(text: str) -> list[str]:
    return [w for w in re.findall(r"[a-zA-Z]{3,}", text.lower())]


def _extract_json(text: str) -> dict[str, Any] | None:
    text = text.strip()
    # strip ```json fences
    fence = re.search(r"```(?:json)?\s*(\{.*\})\s*```", text, re.DOTALL)
    if fence:
        text = fence.group(1)
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1:
        return None
    try:
        return json.loads(text[start:end + 1])
    except json.JSONDecodeError:
        return None


class WorkflowGenerator:
    def __init__(self, settings: Settings, registry: ToolRegistry) -> None:
        self._settings = settings
        self._registry = registry

    # --- public API ---
    async def generate(self, prompt: str) -> Workflow:
        candidates = self._discover_tools(prompt)
        spec = await self._llm_graph(prompt, candidates)
        if spec is None:
            logger.info("AI builder falling back to heuristic generation.")
            spec = self._heuristic_graph(prompt, candidates)
        return self._to_workflow(prompt, spec)

    # --- step 2: discover tools ---
    def _discover_tools(self, prompt: str) -> list[Any]:
        seen: dict[str, Any] = {}
        for kw in _keywords(prompt):
            for m in self._registry.search(kw):
                seen[m.id] = m
        ranked = list(seen.values())[:40]
        if not ranked:
            ranked = self._registry.all()[:40]
        return ranked

    # --- step 3: graph via LLM ---
    async def _llm_graph(self, prompt: str, candidates: list[Any]) -> dict[str, Any] | None:
        try:
            llm = self._resolve_llm()
        except Exception as exc:  # noqa: BLE001
            logger.warning("AI builder: no LLM (%s)", exc)
            return None

        catalog = "\n".join(f"- tool.{m.id}: {m.display_name} — {m.description[:120]}"
                            for m in candidates)
        system = (
            "You are a workflow architect for the ClawFlow platform. Given a brief, "
            "design a directed acyclic workflow graph. Respond with STRICT JSON only, "
            "no prose, matching: {\"name\": str, \"description\": str, "
            "\"nodes\": [{\"id\": str, \"type\": str, \"label\": str, \"config\": {}}], "
            "\"edges\": [{\"source\": str, \"target\": str, \"sourceHandle\": str|null}]}. "
            "Always start with exactly one trigger node. Use tool ids from the catalog."
        )
        human = f"{_TAXONOMY}\n\nTool catalog:\n{catalog}\n\nBrief:\n{prompt}"
        try:
            resp = await llm.ainvoke([("system", system), ("human", human)])
            text = getattr(resp, "content", str(resp))
            if isinstance(text, list):  # some providers return content blocks
                text = " ".join(str(t) for t in text)
            return _extract_json(text)
        except Exception as exc:  # noqa: BLE001
            logger.warning("AI builder LLM call failed: %s", exc)
            return None

    def _resolve_llm(self) -> Any:
        from ..llm import resolve_chat_model

        return resolve_chat_model(
            provider=self._settings.default_llm_provider,
            model=self._settings.default_llm_model,
            temperature=0.0,
        )

    # --- step 3 fallback: heuristic linear graph ---
    def _heuristic_graph(self, prompt: str, candidates: list[Any]) -> dict[str, Any]:
        low = prompt.lower()
        trigger = "trigger.email" if "email" in low else (
            "trigger.cron" if any(w in low for w in ("schedule", "daily", "every")) else
            "trigger.manual")
        nodes = [{"id": "n1", "type": trigger, "label": "Trigger", "config": {}}]
        edges = []
        prev = "n1"
        for i, m in enumerate(candidates[:3], start=2):
            nid = f"n{i}"
            nodes.append({"id": nid, "type": f"tool.{m.id}",
                          "label": m.display_name, "config": {}})
            edges.append({"source": prev, "target": nid, "sourceHandle": None})
            prev = nid
        # Always end with a report so the run produces an artifact.
        nodes.append({"id": "n_report", "type": "action.generate_report",
                      "label": "Generate Report",
                      "config": {"title": "Workflow Result", "format": "markdown"}})
        edges.append({"source": prev, "target": "n_report", "sourceHandle": None})
        return {"name": prompt[:60] or "Generated Workflow",
                "description": f"Auto-generated from: {prompt}",
                "nodes": nodes, "edges": edges}

    # --- step 4: validate + auto-layout ---
    def _to_workflow(self, prompt: str, spec: dict[str, Any]) -> Workflow:
        raw_nodes = spec.get("nodes", [])
        nodes: list[WorkflowNode] = []
        for i, n in enumerate(raw_nodes):
            data = {"label": n.get("label", n.get("type", "")),
                    "config": n.get("config", {})}
            if str(n.get("type", "")).startswith("agent."):
                data["agent_id"] = n.get("agent_id")
            nodes.append(WorkflowNode(
                id=str(n.get("id", f"n{i+1}")),
                type=n.get("type", "trigger.manual"),
                position={"x": (i % 5) * 240, "y": (i // 5) * 160},
                data=data,
            ))
        edges = [WorkflowEdge(source=str(e["source"]), target=str(e["target"]),
                              sourceHandle=e.get("sourceHandle"))
                 for e in spec.get("edges", []) if e.get("source") and e.get("target")]
        return Workflow(
            name=spec.get("name") or (prompt[:60] or "Generated Workflow"),
            description=spec.get("description", prompt),
            nodes=nodes, edges=edges, tags=["ai-generated"],
        )
