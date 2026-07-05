"""
WorkflowServer.py
=================
Extended SSE Workflow Server built on server.py patterns.
Loads real workflows from store/myworkflow.json and executes
their actual nodes in topological order.

All three WorkflowModes are supported:
  FULL_NO_SSE  – synchronous, blocks until complete
  FULL_WITH_SSE – async, continuous SSE progress
  STEP_MODE    – async, pauses after every node (awaiting_resume)

Input-required nodes (agent-start, human_in_the_loop, null properties)
pause execution and emit `awaiting_input` SSE events so the React UI
can collect values before continuing.

Endpoints:
  GET  /health
  GET  /workflows                              – list all workflows
  GET  /workflows/{workflow_id}                – single workflow definition
  POST /workflows/{workflow_id}/execute        – start execution
  POST /execution/{execution_id}/input         – provide input to waiting node
  POST /execution/{execution_id}/resume        – advance STEP_MODE
  GET  /execution/{execution_id}/status        – poll status
  GET  /events/{execution_id}                  – SSE stream
"""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, AsyncGenerator, Dict, List, Optional

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

# ── Logging ────────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)-8s] %(name)s: %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
log = logging.getLogger("workflow_server")

# ── Constants ──────────────────────────────────────────────────────────────────

STORE_PATH = Path(__file__).parent / "store" / "myworkflow.json"
HEARTBEAT_INTERVAL: float = 15.0
SSE_RETRY_MS: int = 3_000
NODE_EXEC_SECONDS: float = 0.8          # simulated node work duration
INPUT_WAIT_TIMEOUT: float = 600.0       # seconds to wait for human input
RESUME_WAIT_TIMEOUT: float = 300.0      # seconds to wait for STEP_MODE resume


# ── Enums ──────────────────────────────────────────────────────────────────────

class WorkflowMode(str, Enum):
    FULL_NO_SSE   = "FULL_NO_SSE"
    FULL_WITH_SSE = "FULL_WITH_SSE"
    STEP_MODE     = "STEP_MODE"


class ExecutionStatus(str, Enum):
    PENDING        = "PENDING"
    RUNNING        = "RUNNING"
    AWAITING_INPUT = "AWAITING_INPUT"
    PAUSED         = "PAUSED"
    COMPLETED      = "COMPLETED"
    FAILED         = "FAILED"


# ── Pydantic models ────────────────────────────────────────────────────────────

class ExecuteRequest(BaseModel):
    mode: WorkflowMode
    initial_inputs: Optional[Dict[str, Any]] = None


class InputRequest(BaseModel):
    node_id: str
    input_data: Dict[str, Any]


class ResumeResponse(BaseModel):
    execution_id: str
    resumed_from_step: int
    status: ExecutionStatus
    message: str


class NodeResult(BaseModel):
    node_id: str
    node_name: str
    node_type: str
    status: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    data: Optional[Dict[str, Any]] = None
    input_received: Optional[Dict[str, Any]] = None


class ExecutionStatusResponse(BaseModel):
    execution_id: str
    workflow_id: str
    workflow_name: str
    mode: WorkflowMode
    status: ExecutionStatus
    current_node_id: Optional[str]
    current_step: int
    total_steps: int
    completed_nodes: List[str]
    results: List[NodeResult]
    error: Optional[str] = None


# ── SSE wire-format helper ─────────────────────────────────────────────────────

def _sse(event: str, data: Any) -> str:
    payload = data if isinstance(data, str) else json.dumps(data, default=str)
    return f"retry:{SSE_RETRY_MS}\nevent:{event}\ndata:{payload}\n\n"


# ── Workflow store ─────────────────────────────────────────────────────────────

def _load_workflows() -> Dict[str, dict]:
    raw = json.loads(STORE_PATH.read_text(encoding="utf-8"))
    return {wf["id"]: wf for wf in raw}


_WORKFLOWS: Dict[str, dict] = {}


# ── Graph helpers ──────────────────────────────────────────────────────────────

def topological_sort(nodes: List[dict], edges: List[dict]) -> List[str]:
    """Return node IDs in execution order (Kahn's BFS)."""
    node_ids = [n["id"] for n in nodes]
    in_degree: Dict[str, int] = {nid: 0 for nid in node_ids}
    adj: Dict[str, List[str]] = {nid: [] for nid in node_ids}

    for edge in edges:
        src, tgt = edge["source"], edge["target"]
        if src in adj and tgt in in_degree:
            adj[src].append(tgt)
            in_degree[tgt] += 1

    queue = [nid for nid in node_ids if in_degree[nid] == 0]
    result: List[str] = []
    visited: set = set()

    while queue:
        nid = queue.pop(0)
        if nid in visited:
            continue
        visited.add(nid)
        result.append(nid)
        for neighbor in adj[nid]:
            in_degree[neighbor] -= 1
            if in_degree[neighbor] == 0:
                queue.append(neighbor)

    # Append any unreachable nodes (cycle-safe fallback)
    for nid in node_ids:
        if nid not in visited:
            result.append(nid)

    return result


def _node_needs_input(node: dict) -> bool:
    """True when the node should pause and collect user input via SSE."""
    data = node.get("data", {})
    agent_id = node.get("agent_id") or ""
    node_type = data.get("type", "")

    # Start nodes: request run_label / environment confirmation
    if agent_id == "agent-start":
        return True

    # Human-in-the-loop: always requires a human decision
    if node_type == "human_in_the_loop":
        return True

    # Any property explicitly null or empty string
    props = data.get("properties") or {}
    for val in props.values():
        if val is None or val == "" or val == []:
            return True

    return False


def _required_fields(node: dict) -> List[dict]:
    """Describe what the UI must collect for this input-required node."""
    data = node.get("data", {})
    agent_id = node.get("agent_id") or ""
    node_type = data.get("type", "")
    props = data.get("properties") or {}

    if agent_id == "agent-start":
        return [
            {
                "key": "run_label",
                "label": "Run Label",
                "type": "text",
                "required": False,
                "current": props.get("run_label", ""),
                "placeholder": "e.g. test-run-1",
            },
            {
                "key": "environment",
                "label": "Environment",
                "type": "select",
                "options": ["production", "staging", "development"],
                "required": True,
                "current": props.get("environment", "production"),
            },
        ]

    if node_type == "human_in_the_loop":
        return [
            {
                "key": "decision",
                "label": "Decision",
                "type": "select",
                "options": ["approve", "reject", "escalate"],
                "required": True,
                "current": None,
            },
            {
                "key": "comments",
                "label": "Reviewer Comments",
                "type": "textarea",
                "required": False,
                "current": "",
                "placeholder": "Optional notes for downstream agents",
            },
        ]

    # Null-property fields
    fields = []
    for key, val in props.items():
        if val is None or val == "" or val == []:
            fields.append({
                "key": key,
                "label": key.replace("_", " ").title(),
                "type": "text",
                "required": True,
                "current": val,
                "placeholder": f"Provide value for {key}",
            })
    return fields


def _simulate_result(node: dict, input_data: dict) -> dict:
    """Produce a deterministic simulated result for a node execution."""
    data = node.get("data", {})
    node_type = data.get("type", "")
    name = data.get("name", node["id"])

    _by_type: Dict[str, dict] = {
        "start":            {"status": "initialized", "message": f"Workflow initialized with config"},
        "end":              {"status": "finalized",   "message": f"Workflow output collected"},
        "automatic":        {"status": "processed",   "records_processed": 128, "duration_ms": 412},
        "human_in_the_loop":{"status": "reviewed",    "decision": input_data.get("decision", "approved"),
                             "comments": input_data.get("comments", "")},
        "prompt_agent":     {"status": "generated",   "tokens_used": 1024, "model": data.get("properties", {}).get("model", "llm")},
        "react_agent":      {"status": "completed",   "iterations": 3,     "tool_calls": 5},
        "reflection_agent": {"status": "improved",    "quality_score": 8.5, "revisions": 1},
        "guardrails":       {"status": "passed",      "pii_found": False,   "toxicity_found": False},
        "supervisor":       {"status": "monitoring",  "agents_healthy": 2,  "failures_caught": 0},
        "orchestrator":     {"status": "dispatched",  "sub_tasks_created": 2},
        "conditional":      {"status": "routed",      "branch_taken": "default"},
    }
    base = dict(_by_type.get(node_type, {"status": "completed"}))
    base["node_name"] = name
    return base


# ── WorkflowExecution ──────────────────────────────────────────────────────────

class WorkflowExecution:
    """State machine for a single running workflow instance."""

    def __init__(self, execution_id: str, workflow: dict, mode: WorkflowMode) -> None:
        self.execution_id = execution_id
        self.workflow = workflow
        self.mode = mode
        self.status = ExecutionStatus.PENDING
        self.error: Optional[str] = None

        self.sorted_node_ids: List[str] = topological_sort(
            workflow["nodes"], workflow["edges"]
        )
        self.node_map: Dict[str, dict] = {n["id"]: n for n in workflow["nodes"]}

        self.current_node_id: Optional[str] = None
        self.current_step: int = 0
        self.completed_nodes: List[str] = []
        self.results: List[NodeResult] = []

        # SSE per-subscriber queues
        self._sse_queues: List[asyncio.Queue[str]] = []

        # Replay buffer — stores every SSE message in emission order so that
        # a subscriber who connects *after* execution has already started still
        # receives workflow_started / node_started / awaiting_input etc.
        self._event_buffer: List[str] = []

        # Synchronisation events
        self._input_event: asyncio.Event = asyncio.Event()
        self._resume_event: asyncio.Event = asyncio.Event()
        self._pending_input: Dict[str, Any] = {}

        self._task: Optional[asyncio.Task[None]] = None

    # ── SSE subscriber management ──────────────────────────────────────────────

    def add_subscriber(self) -> asyncio.Queue[str]:
        q: asyncio.Queue[str] = asyncio.Queue(maxsize=500)
        # Replay all events emitted so far so late-joining subscribers
        # (including the very first subscriber who misses the initial burst)
        # receive the complete event history before live messages.
        for msg in self._event_buffer:
            try:
                q.put_nowait(msg)
            except asyncio.QueueFull:
                break
        self._sse_queues.append(q)
        return q

    def remove_subscriber(self, q: asyncio.Queue[str]) -> None:
        try:
            self._sse_queues.remove(q)
        except ValueError:
            pass

    async def broadcast(self, event: str, data: Any) -> None:
        if self.mode == WorkflowMode.FULL_NO_SSE:
            return
        msg = _sse(event, data)
        self._event_buffer.append(msg)   # buffer for late subscribers
        for q in list(self._sse_queues):
            try:
                q.put_nowait(msg)
            except asyncio.QueueFull:
                log.warning("SSE queue full, dropping '%s' for %s", event, self.execution_id)

    # ── STEP_MODE resume ───────────────────────────────────────────────────────

    def signal_resume(self) -> bool:
        if self.status != ExecutionStatus.PAUSED:
            return False
        self._resume_event.set()
        return True

    # ── Input provision ────────────────────────────────────────────────────────

    def provide_input(self, node_id: str, input_data: dict) -> bool:
        if self.status != ExecutionStatus.AWAITING_INPUT:
            return False
        if self.current_node_id != node_id:
            return False
        self._pending_input = input_data
        self._input_event.set()
        return True

    # ── Main execution loop ────────────────────────────────────────────────────

    async def run(self, initial_inputs: Optional[dict] = None) -> None:
        self.status = ExecutionStatus.RUNNING
        total = len(self.sorted_node_ids)

        log.info("Execution %s STARTED  workflow=%s  mode=%s  nodes=%d",
                 self.execution_id, self.workflow["name"], self.mode, total)

        await self.broadcast("workflow_started", {
            "execution_id": self.execution_id,
            "workflow_id": self.workflow["id"],
            "workflow_name": self.workflow["name"],
            "mode": self.mode,
            "total_nodes": total,
            "node_names": [self.node_map[nid]["data"].get("name", nid)
                           for nid in self.sorted_node_ids],
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

        try:
            for step_idx, node_id in enumerate(self.sorted_node_ids):
                node = self.node_map[node_id]
                self.current_node_id = node_id
                self.current_step = step_idx + 1
                data = node.get("data", {})
                node_name = data.get("name", node_id)
                node_type = data.get("type", "")

                log.info("Execution %s  step=%d/%d  node=%s  type=%s",
                         self.execution_id, step_idx + 1, total, node_name, node_type)

                await self.broadcast("node_started", {
                    "execution_id": self.execution_id,
                    "node_id": node_id,
                    "node_name": node_name,
                    "node_type": node_type,
                    "agent_id": node.get("agent_id"),
                    "tool_id": node.get("tool_id"),
                    "step": step_idx + 1,
                    "total": total,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })

                # ── Collect input if required ──────────────────────────────
                node_input: dict = {}
                if _node_needs_input(node):
                    self.status = ExecutionStatus.AWAITING_INPUT
                    req_fields = _required_fields(node)

                    await self.broadcast("awaiting_input", {
                        "execution_id": self.execution_id,
                        "node_id": node_id,
                        "node_name": node_name,
                        "node_type": node_type,
                        "agent_id": node.get("agent_id"),
                        "required_fields": req_fields,
                        "current_properties": data.get("properties") or {},
                        "step": step_idx + 1,
                        "total": total,
                        "message": f"'{node_name}' requires input before executing.",
                        "submit_url": f"/execution/{self.execution_id}/input",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    })

                    log.info("Execution %s AWAITING_INPUT  node=%s", self.execution_id, node_name)
                    self._input_event.clear()

                    try:
                        await asyncio.wait_for(
                            self._input_event.wait(), timeout=INPUT_WAIT_TIMEOUT
                        )
                    except asyncio.TimeoutError:
                        raise RuntimeError(
                            f"Input timeout ({INPUT_WAIT_TIMEOUT}s) for node '{node_name}'"
                        )

                    node_input = dict(self._pending_input)
                    self._pending_input = {}
                    self.status = ExecutionStatus.RUNNING
                    log.info("Execution %s INPUT_RECEIVED  node=%s", self.execution_id, node_name)

                # ── Simulate node work ─────────────────────────────────────
                await asyncio.sleep(NODE_EXEC_SECONDS)

                sim = _simulate_result(node, node_input)
                result = NodeResult(
                    node_id=node_id,
                    node_name=node_name,
                    node_type=node_type,
                    status=sim.get("status", "completed"),
                    data=sim,
                    input_received=node_input or None,
                )
                self.results.append(result)
                self.completed_nodes.append(node_id)

                await self.broadcast("node_completed", {
                    "execution_id": self.execution_id,
                    "node_id": node_id,
                    "node_name": node_name,
                    "node_type": node_type,
                    "step": step_idx + 1,
                    "total": total,
                    "result": sim,
                    "input_received": node_input or None,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })

                # ── STEP_MODE: pause before next node ──────────────────────
                if self.mode == WorkflowMode.STEP_MODE and step_idx < total - 1:
                    self.status = ExecutionStatus.PAUSED
                    self._resume_event.clear()
                    next_node = self.node_map.get(self.sorted_node_ids[step_idx + 1], {})
                    next_name = next_node.get("data", {}).get("name", "next node")

                    await self.broadcast("awaiting_resume", {
                        "execution_id": self.execution_id,
                        "node_id": node_id,
                        "node_name": node_name,
                        "step": step_idx + 1,
                        "next_step": step_idx + 2,
                        "next_node_name": next_name,
                        "total": total,
                        "message": (
                            f"Paused after '{node_name}'. "
                            f"POST /execution/{self.execution_id}/resume to continue."
                        ),
                        "resume_url": f"/execution/{self.execution_id}/resume",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    })

                    log.info("Execution %s PAUSED  step=%d", self.execution_id, step_idx + 1)

                    try:
                        await asyncio.wait_for(
                            self._resume_event.wait(), timeout=RESUME_WAIT_TIMEOUT
                        )
                    except asyncio.TimeoutError:
                        raise RuntimeError(
                            f"Resume timeout ({RESUME_WAIT_TIMEOUT}s) after step {step_idx + 1}"
                        )

                    self.status = ExecutionStatus.RUNNING
                    log.info("Execution %s RESUMED  next_step=%d", self.execution_id, step_idx + 2)

            # ── All nodes done ─────────────────────────────────────────────
            self.status = ExecutionStatus.COMPLETED
            self.current_node_id = None

            await self.broadcast("workflow_completed", {
                "execution_id": self.execution_id,
                "workflow_id": self.workflow["id"],
                "workflow_name": self.workflow["name"],
                "total_nodes": total,
                "message": "All nodes completed successfully!",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })
            log.info("Execution %s COMPLETED", self.execution_id)

        except asyncio.CancelledError:
            self.status = ExecutionStatus.FAILED
            self.error = "Workflow cancelled"
            await self.broadcast("workflow_failed", {
                "execution_id": self.execution_id,
                "message": "Workflow was cancelled",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })
            log.warning("Execution %s CANCELLED", self.execution_id)
            raise

        except Exception as exc:
            self.status = ExecutionStatus.FAILED
            self.error = str(exc)
            await self.broadcast("workflow_failed", {
                "execution_id": self.execution_id,
                "message": f"Workflow failed: {exc}",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })
            log.exception("Execution %s FAILED", self.execution_id)


# ── Execution Manager ──────────────────────────────────────────────────────────

class ExecutionManager:
    def __init__(self) -> None:
        self._executions: Dict[str, WorkflowExecution] = {}

    def create(self, workflow: dict, mode: WorkflowMode) -> WorkflowExecution:
        execution_id = str(uuid.uuid4())
        ex = WorkflowExecution(execution_id, workflow, mode)
        self._executions[execution_id] = ex
        return ex

    def get(self, execution_id: str) -> Optional[WorkflowExecution]:
        return self._executions.get(execution_id)

    def cancel_all(self) -> None:
        for ex in self._executions.values():
            if ex._task and not ex._task.done():
                ex._task.cancel()


_manager = ExecutionManager()


# ── Lifespan ───────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    global _WORKFLOWS
    _WORKFLOWS = _load_workflows()
    log.info("Loaded %d workflows from %s", len(_WORKFLOWS), STORE_PATH)
    yield
    log.info("Shutting down – cancelling all executions")
    _manager.cancel_all()


# ── FastAPI app ────────────────────────────────────────────────────────────────

app = FastAPI(
    title="Workflow Server",
    description=(
        "SSE + REST workflow execution engine. Loads workflow definitions from "
        "store/myworkflow.json and executes them node-by-node with full SSE streaming. "
        "Supports FULL_NO_SSE, FULL_WITH_SSE, and STEP_MODE. "
        "Input-required nodes (agent-start, human_in_the_loop, null properties) "
        "pause and emit awaiting_input events for the UI to handle."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Health ─────────────────────────────────────────────────────────────────────

@app.get("/health", tags=["ops"])
async def health() -> dict:
    return {
        "status": "ok",
        "workflows_loaded": len(_WORKFLOWS),
        "active_executions": len(_manager._executions),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# ── Workflow listing ───────────────────────────────────────────────────────────

@app.get("/workflows", tags=["workflows"])
async def list_workflows() -> list:
    """Return all workflow definitions from the store."""
    return [
        {
            "id": wf["id"],
            "name": wf["name"],
            "description": wf.get("description", ""),
            "status": wf.get("status", "draft"),
            "tags": wf.get("tags", []),
            "node_count": len(wf.get("nodes", [])),
            "edge_count": len(wf.get("edges", [])),
        }
        for wf in _WORKFLOWS.values()
    ]


@app.get("/workflows/{workflow_id}", tags=["workflows"])
async def get_workflow(workflow_id: str) -> dict:
    """Return the full workflow definition including nodes and edges."""
    wf = _WORKFLOWS.get(workflow_id)
    if not wf:
        raise HTTPException(status_code=404, detail=f"Workflow '{workflow_id}' not found")
    return wf


# ── Execute workflow ───────────────────────────────────────────────────────────

@app.post("/workflows/{workflow_id}/execute", tags=["execution"])
async def execute_workflow(workflow_id: str, req: ExecuteRequest) -> dict:
    """
    Start executing a workflow.

    - **FULL_NO_SSE**   – blocks until all nodes finish, returns final status.
    - **FULL_WITH_SSE** – launches background task; connect to `/events/{execution_id}`.
    - **STEP_MODE**     – launches background task; pauses after every node until
      `POST /execution/{execution_id}/resume` is called.

    Input-required nodes (agent-start, human_in_the_loop, null properties) will
    additionally pause and emit `awaiting_input` SSE events regardless of mode.
    """
    wf = _WORKFLOWS.get(workflow_id)
    if not wf:
        raise HTTPException(status_code=404, detail=f"Workflow '{workflow_id}' not found")

    ex = _manager.create(wf, req.mode)

    if req.mode == WorkflowMode.FULL_NO_SSE:
        try:
            await ex.run(req.initial_inputs)
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc
        return {
            "execution_id": ex.execution_id,
            "workflow_id": workflow_id,
            "workflow_name": wf["name"],
            "mode": req.mode,
            "status": ex.status,
            "message": f"Workflow completed. GET /execution/{ex.execution_id}/status for results.",
        }

    ex._task = asyncio.create_task(
        ex.run(req.initial_inputs),
        name=f"workflow-{ex.execution_id}",
    )
    return {
        "execution_id": ex.execution_id,
        "workflow_id": workflow_id,
        "workflow_name": wf["name"],
        "mode": req.mode,
        "status": ExecutionStatus.PENDING,
        "message": (
            f"Execution started. "
            f"Connect to GET /events/{ex.execution_id} for live updates."
        ),
        "sse_url": f"/events/{ex.execution_id}",
        "status_url": f"/execution/{ex.execution_id}/status",
    }


# ── Provide input ──────────────────────────────────────────────────────────────

@app.post("/execution/{execution_id}/input", tags=["execution"])
async def provide_input(execution_id: str, req: InputRequest) -> dict:
    """
    Supply input data for a node that is currently in AWAITING_INPUT state.
    The execution resumes automatically once input is received.
    """
    ex = _manager.get(execution_id)
    if ex is None:
        raise HTTPException(status_code=404, detail=f"Execution '{execution_id}' not found")
    if ex.status != ExecutionStatus.AWAITING_INPUT:
        raise HTTPException(
            status_code=409,
            detail=f"Execution is not awaiting input (current status: {ex.status})",
        )
    if not ex.provide_input(req.node_id, req.input_data):
        raise HTTPException(
            status_code=409,
            detail=f"Node '{req.node_id}' is not the current awaiting node ({ex.current_node_id})",
        )
    return {
        "execution_id": execution_id,
        "node_id": req.node_id,
        "status": "input_accepted",
        "message": "Input accepted; node execution will resume.",
    }


# ── Resume (STEP_MODE) ─────────────────────────────────────────────────────────

@app.post("/execution/{execution_id}/resume", tags=["execution"])
async def resume_execution(execution_id: str) -> ResumeResponse:
    """Resume a STEP_MODE execution that is paused after a node."""
    ex = _manager.get(execution_id)
    if ex is None:
        raise HTTPException(status_code=404, detail=f"Execution '{execution_id}' not found")
    if ex.mode != WorkflowMode.STEP_MODE:
        raise HTTPException(
            status_code=400,
            detail=f"Resume is only valid for STEP_MODE (current mode: {ex.mode})",
        )
    step = ex.current_step
    if not ex.signal_resume():
        raise HTTPException(
            status_code=409,
            detail=f"Execution is not paused (current status: {ex.status})",
        )
    return ResumeResponse(
        execution_id=execution_id,
        resumed_from_step=step,
        status=ExecutionStatus.RUNNING,
        message=f"Resumed from step {step}; step {step + 1} will begin shortly.",
    )


# ── Status polling ─────────────────────────────────────────────────────────────

@app.get("/execution/{execution_id}/status", response_model=ExecutionStatusResponse, tags=["execution"])
async def get_status(execution_id: str) -> ExecutionStatusResponse:
    """Poll the current status and accumulated results for any execution."""
    ex = _manager.get(execution_id)
    if ex is None:
        raise HTTPException(status_code=404, detail=f"Execution '{execution_id}' not found")
    return ExecutionStatusResponse(
        execution_id=execution_id,
        workflow_id=ex.workflow["id"],
        workflow_name=ex.workflow["name"],
        mode=ex.mode,
        status=ex.status,
        current_node_id=ex.current_node_id,
        current_step=ex.current_step,
        total_steps=len(ex.sorted_node_ids),
        completed_nodes=ex.completed_nodes,
        results=ex.results,
        error=ex.error,
    )


# ── SSE stream ─────────────────────────────────────────────────────────────────

@app.get("/events/{execution_id}", tags=["sse"])
async def sse_stream(execution_id: str, request: Request) -> StreamingResponse:
    """
    Long-lived SSE stream for a running workflow execution.
    Not available for FULL_NO_SSE mode (returns HTTP 400).

    Multiple subscribers may connect to the same execution_id simultaneously.

    Events emitted:
      connected        – handshake on connect
      workflow_started – execution begun with node list
      node_started     – a node is about to execute
      awaiting_input   – node needs user input (FULL_WITH_SSE & STEP_MODE)
      node_completed   – node finished with result data
      awaiting_resume  – STEP_MODE: paused, waiting for resume call
      workflow_completed – all nodes done
      workflow_failed  – error occurred
      (comment)        – heartbeat keep-alive every 15s
    """
    ex = _manager.get(execution_id)
    if ex is None:
        raise HTTPException(status_code=404, detail=f"Execution '{execution_id}' not found")
    if ex.mode == WorkflowMode.FULL_NO_SSE:
        raise HTTPException(
            status_code=400,
            detail="SSE streaming is not available for FULL_NO_SSE executions",
        )

    q = ex.add_subscriber()
    log.info("SSE subscriber connected  execution_id=%s", execution_id)

    async def _heartbeat(queue: asyncio.Queue[str]) -> None:
        while True:
            await asyncio.sleep(HEARTBEAT_INTERVAL)
            ts = datetime.now(timezone.utc).isoformat()
            try:
                queue.put_nowait(f": heartbeat {ts}\n\n")
            except asyncio.QueueFull:
                pass

    _TERMINAL = frozenset({"workflow_completed", "workflow_failed"})

    async def _generator() -> AsyncGenerator[str, None]:
        yield _sse("connected", {
            "execution_id": execution_id,
            "workflow_id": ex.workflow["id"],
            "workflow_name": ex.workflow["name"],
            "mode": ex.mode,
            "message": "SSE stream open",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

        hb_task = asyncio.create_task(_heartbeat(q))
        terminal_seen = False
        try:
            while True:
                if await request.is_disconnected():
                    log.info("SSE client disconnected  execution_id=%s", execution_id)
                    break
                if terminal_seen and q.empty():
                    break
                try:
                    msg = await asyncio.wait_for(q.get(), timeout=1.0)
                except asyncio.TimeoutError:
                    continue
                yield msg
                if any(f"event:{ev}" in msg for ev in _TERMINAL):
                    terminal_seen = True
        finally:
            hb_task.cancel()
            ex.remove_subscriber(q)
            log.info("SSE subscriber removed  execution_id=%s", execution_id)

    return StreamingResponse(
        _generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


# ── Entry point ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    uvicorn.run(
        "WorkflowServer:app",
        host="0.0.0.0",
        port=8001,
        reload=False,
        log_level="info",
        access_log=True,
    )
