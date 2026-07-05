"""
SSE Workflow Server
===================
FastAPI + SSE server supporting a 10-step long-running workflow in three modes:
  - FULL_NO_SSE   : synchronous execution, no progress events
  - FULL_WITH_SSE : async execution, continuous SSE progress updates
  - STEP_MODE     : async execution, pauses after each step, waits for client resume

Endpoints:
  POST /workflow/start                           – start a workflow
  POST /workflow/{workflow_execution_id}/resume  – resume a paused STEP_MODE workflow
  GET  /workflow/{workflow_execution_id}/status  – poll current status & results
  GET  /events/{workflow_execution_id}           – SSE stream for a workflow execution
  GET  /health                                   – liveness probe
"""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from enum import Enum
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
log = logging.getLogger("sse_workflow.server")

# ── Constants ──────────────────────────────────────────────────────────────────

TOTAL_STEPS: int = 10
STEP_DURATION_SECONDS: float = 1.0   # simulated work per step
HEARTBEAT_INTERVAL: float = 15.0     # SSE keep-alive interval (seconds)
SSE_RETRY_MS: int = 3_000            # SSE client-side retry hint (ms)
STEP_MODE_RESUME_TIMEOUT: float = 300.0  # max seconds to wait for a resume call


# ── Enums & Pydantic models ────────────────────────────────────────────────────

class WorkflowMode(str, Enum):
    FULL_NO_SSE = "FULL_NO_SSE"
    FULL_WITH_SSE = "FULL_WITH_SSE"
    STEP_MODE = "STEP_MODE"


class SessionStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class StepResult(BaseModel):
    step: int
    status: str
    message: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    data: Optional[Dict[str, Any]] = None


class WorkflowRequest(BaseModel):
    mode: WorkflowMode


class WorkflowResponse(BaseModel):
    workflow_execution_id: str
    mode: WorkflowMode
    status: SessionStatus
    message: str


class ResumeResponse(BaseModel):
    workflow_execution_id: str
    resumed_from_step: int
    status: SessionStatus
    message: str


class StatusResponse(BaseModel):
    workflow_execution_id: str
    mode: WorkflowMode
    status: SessionStatus
    current_step: int
    total_steps: int
    results: List[StepResult]
    error: Optional[str] = None


# ── SSE wire-format helper ─────────────────────────────────────────────────────

def _sse_format(event: str, data: Any, retry: int = SSE_RETRY_MS) -> str:
    """Encode *data* as an SSE message string (including double-newline terminator)."""
    payload = data if isinstance(data, str) else json.dumps(data, default=str)
    return f"retry:{retry}\nevent:{event}\ndata:{payload}\n\n"


# ── WorkflowSession ────────────────────────────────────────────────────────────

class WorkflowSession:
    """Holds all state for a single workflow execution."""

    def __init__(self, workflow_execution_id: str, mode: WorkflowMode) -> None:
        self.workflow_execution_id = workflow_execution_id
        self.mode = mode
        self.status = SessionStatus.PENDING
        self.current_step: int = 0
        self.results: List[StepResult] = []
        self.error: Optional[str] = None

        # STEP_MODE synchronisation
        self._resume_event: asyncio.Event = asyncio.Event()

        # Per-subscriber SSE queues  (one queue per connected client)
        self._sse_queues: List[asyncio.Queue[str]] = []

        # Background asyncio.Task reference (for cancellation)
        self._task: Optional[asyncio.Task[None]] = None

    # ── SSE subscriber management ──────────────────────────────────────────

    def add_subscriber(self) -> asyncio.Queue[str]:
        q: asyncio.Queue[str] = asyncio.Queue(maxsize=200)
        self._sse_queues.append(q)
        return q

    def remove_subscriber(self, q: asyncio.Queue[str]) -> None:
        try:
            self._sse_queues.remove(q)
        except ValueError:
            pass

    # ── Broadcasting ───────────────────────────────────────────────────────

    async def broadcast(self, event: str, data: Any) -> None:
        """Push an SSE message to every connected subscriber queue."""
        if self.mode == WorkflowMode.FULL_NO_SSE:
            return  # silent mode – never broadcast
        msg = _sse_format(event, data)
        for q in list(self._sse_queues):
            try:
                q.put_nowait(msg)
            except asyncio.QueueFull:
                log.warning(
                    "SSE queue full for workflow_execution_id %s – dropping event '%s'",
                    self.workflow_execution_id,
                    event,
                )

    # ── STEP_MODE resume ───────────────────────────────────────────────────

    def signal_resume(self) -> bool:
        """Unblock a paused STEP_MODE workflow. Returns False when not paused."""
        if self.status != SessionStatus.PAUSED:
            return False
        self._resume_event.set()
        return True

    # ── Workflow execution ─────────────────────────────────────────────────

    async def run(self) -> None:
        self.status = SessionStatus.RUNNING
        log.info(
            "Workflow %s STARTED  mode=%s  total_steps=%d",
            self.workflow_execution_id,
            self.mode,
            TOTAL_STEPS,
        )
        try:
            for step in range(1, TOTAL_STEPS + 1):
                self.current_step = step
                log.info(
                    "Execution %s: executing step %d/%d",
                    self.workflow_execution_id,
                    step,
                    TOTAL_STEPS,
                )

                await self.broadcast(
                    "step_started",
                    {
                        "workflow_execution_id": self.workflow_execution_id,
                        "step": step,
                        "total": TOTAL_STEPS,
                        "message": f"Step {step} started",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    },
                )

                # ── Simulate step work ──────────────────────────────────
                await asyncio.sleep(STEP_DURATION_SECONDS)

                result = StepResult(
                    step=step,
                    status="completed",
                    message=f"Step {step} completed successfully",
                    data={"output": f"result_step_{step}", "processed_items": step * 100},
                )
                self.results.append(result)

                await self.broadcast(
                    "step_completed",
                    {
                        "workflow_execution_id": self.workflow_execution_id,
                        "step": step,
                        "total": TOTAL_STEPS,
                        "message": result.message,
                        "data": result.data,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    },
                )

                # ── STEP_MODE: pause and wait for resume ───────────────
                if self.mode == WorkflowMode.STEP_MODE and step < TOTAL_STEPS:
                    self.status = SessionStatus.PAUSED
                    self._resume_event.clear()

                    await self.broadcast(
                        "awaiting_resume",
                        {
                            "workflow_execution_id": self.workflow_execution_id,
                            "step": step,
                            "next_step": step + 1,
                            "total": TOTAL_STEPS,
                            "message": (
                                f"Paused after step {step}. "
                                f"POST /workflow/{self.workflow_execution_id}/resume to continue."
                            ),
                            "resume_url": f"/workflow/{self.workflow_execution_id}/resume",
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                        },
                    )
                    log.info(
                        "Execution %s PAUSED after step %d – waiting for resume",
                        self.workflow_execution_id,
                        step,
                    )

                    try:
                        await asyncio.wait_for(
                            self._resume_event.wait(),
                            timeout=STEP_MODE_RESUME_TIMEOUT,
                        )
                    except asyncio.TimeoutError:
                        raise RuntimeError(
                            f"Resume not received within {STEP_MODE_RESUME_TIMEOUT}s "
                            f"after step {step}"
                        )

                    self.status = SessionStatus.RUNNING
                    log.info(
                        "Execution %s RESUMED  next_step=%d",
                        self.workflow_execution_id,
                        step + 1,
                    )

            # ── All steps done ─────────────────────────────────────────────
            self.status = SessionStatus.COMPLETED
            await self.broadcast(
                "workflow_completed",
                {
                    "workflow_execution_id": self.workflow_execution_id,
                    "total_steps": TOTAL_STEPS,
                    "message": "All steps completed successfully!",
                    "results_count": len(self.results),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            )
            log.info("Workflow %s COMPLETED", self.workflow_execution_id)

        except asyncio.CancelledError:
            self.status = SessionStatus.FAILED
            self.error = "Workflow cancelled"
            await self.broadcast(
                "workflow_failed",
                {
                    "workflow_execution_id": self.workflow_execution_id,
                    "message": "Workflow was cancelled",
                },
            )
            log.warning("Workflow %s CANCELLED", self.workflow_execution_id)
            raise

        except Exception as exc:
            self.status = SessionStatus.FAILED
            self.error = str(exc)
            await self.broadcast(
                "workflow_failed",
                {
                    "workflow_execution_id": self.workflow_execution_id,
                    "message": f"Workflow failed: {exc}",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            )
            log.exception("Workflow %s FAILED", self.workflow_execution_id)


# ── Session Manager ────────────────────────────────────────────────────────────

class SessionManager:
    """Thread-safe (single-event-loop) registry of active workflow executions."""

    def __init__(self) -> None:
        self._executions: Dict[str, WorkflowSession] = {}

    def create(self, mode: WorkflowMode) -> WorkflowSession:
        workflow_execution_id = str(uuid.uuid4())
        session = WorkflowSession(workflow_execution_id, mode)
        self._executions[workflow_execution_id] = session
        log.info(
            "Created workflow execution %s  mode=%s", workflow_execution_id, mode
        )
        return session

    def get(self, workflow_execution_id: str) -> Optional[WorkflowSession]:
        return self._executions.get(workflow_execution_id)

    def cancel_all(self) -> None:
        for session in self._executions.values():
            if session._task and not session._task.done():
                session._task.cancel()


_manager = SessionManager()


# ── Lifespan ───────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    log.info("SSE Workflow Server starting up")
    yield
    log.info("SSE Workflow Server shutting down – cancelling all tasks")
    _manager.cancel_all()


# ── FastAPI application ────────────────────────────────────────────────────────

app = FastAPI(
    title="SSE Workflow API",
    description=(
        "Production-grade Server-Sent Events + REST workflow system. "
        "Supports FULL_NO_SSE, FULL_WITH_SSE, and STEP_MODE execution. "
        "Multiple clients can run concurrent workflow executions, each identified "
        "by a unique workflow_execution_id."
    ),
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Health probe ───────────────────────────────────────────────────────────────

@app.get("/health", tags=["ops"])
async def health() -> dict:
    return {
        "status": "ok",
        "active_executions": len(_manager._executions),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# ── Start workflow ─────────────────────────────────────────────────────────────

@app.post("/workflow/start", response_model=WorkflowResponse, tags=["workflow"])
async def start_workflow(req: WorkflowRequest) -> WorkflowResponse:
    """
    Start a new 10-step workflow execution. Returns a unique ``workflow_execution_id``
    that identifies this run. Multiple clients may call this endpoint concurrently;
    each receives its own independent ``workflow_execution_id``.

    - **FULL_NO_SSE** – blocks until all steps finish, returns the final status.
    - **FULL_WITH_SSE** – launches background task; connect to
      `/events/{workflow_execution_id}` for progress.
    - **STEP_MODE**   – launches background task; pauses after each step and waits for
      `POST /workflow/{workflow_execution_id}/resume` before continuing.
    """
    session = _manager.create(req.mode)

    if req.mode == WorkflowMode.FULL_NO_SSE:
        # Run synchronously – caller blocks until workflow completes.
        try:
            await session.run()
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc
        return WorkflowResponse(
            workflow_execution_id=session.workflow_execution_id,
            mode=session.mode,
            status=session.status,
            message=(
                f"Workflow completed synchronously. "
                f"Fetch /workflow/{session.workflow_execution_id}/status for results."
            ),
        )

    # FULL_WITH_SSE / STEP_MODE – run in background
    session._task = asyncio.create_task(
        session.run(), name=f"workflow-{session.workflow_execution_id}"
    )
    return WorkflowResponse(
        workflow_execution_id=session.workflow_execution_id,
        mode=session.mode,
        status=SessionStatus.PENDING,
        message=(
            f"Workflow started in background. "
            f"Connect to GET /events/{session.workflow_execution_id} for live updates."
        ),
    )


# ── Resume (STEP_MODE only) ────────────────────────────────────────────────────

@app.post(
    "/workflow/{workflow_execution_id}/resume",
    response_model=ResumeResponse,
    tags=["workflow"],
)
async def resume_workflow(workflow_execution_id: str) -> ResumeResponse:
    """
    Resume a **STEP_MODE** workflow that is currently paused after a step.
    Returns 409 if the execution is not in PAUSED state.
    """
    session = _manager.get(workflow_execution_id)
    if session is None:
        raise HTTPException(
            status_code=404,
            detail=f"Workflow execution '{workflow_execution_id}' not found",
        )
    if session.mode != WorkflowMode.STEP_MODE:
        raise HTTPException(
            status_code=400,
            detail=f"Resume is only valid for STEP_MODE (execution mode: {session.mode})",
        )
    resumed_from = session.current_step
    if not session.signal_resume():
        raise HTTPException(
            status_code=409,
            detail=f"Execution is not paused (current status: {session.status})",
        )
    log.info(
        "Execution %s RESUME requested from step %d",
        workflow_execution_id,
        resumed_from,
    )
    return ResumeResponse(
        workflow_execution_id=workflow_execution_id,
        resumed_from_step=resumed_from,
        status=SessionStatus.RUNNING,
        message=f"Resumed from step {resumed_from}; step {resumed_from + 1} will begin shortly.",
    )


# ── Status polling ─────────────────────────────────────────────────────────────

@app.get(
    "/workflow/{workflow_execution_id}/status",
    response_model=StatusResponse,
    tags=["workflow"],
)
async def get_status(workflow_execution_id: str) -> StatusResponse:
    """Poll the current status and accumulated results for any workflow execution."""
    session = _manager.get(workflow_execution_id)
    if session is None:
        raise HTTPException(
            status_code=404,
            detail=f"Workflow execution '{workflow_execution_id}' not found",
        )
    return StatusResponse(
        workflow_execution_id=workflow_execution_id,
        mode=session.mode,
        status=session.status,
        current_step=session.current_step,
        total_steps=TOTAL_STEPS,
        results=session.results,
        error=session.error,
    )


# ── SSE stream ─────────────────────────────────────────────────────────────────

@app.get("/events/{workflow_execution_id}", tags=["sse"])
async def sse_stream(workflow_execution_id: str, request: Request) -> StreamingResponse:
    """
    Long-lived SSE stream for a running workflow execution.
    Not available for FULL_NO_SSE executions (HTTP 400).

    Multiple clients can subscribe to the same ``workflow_execution_id``; each
    receives an independent copy of every event via a dedicated queue.

    Events emitted:
      - ``connected``          – handshake on connect
      - ``step_started``       – step is about to execute
      - ``step_completed``     – step finished successfully
      - ``awaiting_resume``    – STEP_MODE only: paused, waiting for resume call
      - ``workflow_completed`` – all steps done
      - ``workflow_failed``    – unrecoverable error
      - (SSE comment)          – heartbeat (invisible to EventSource listeners)
    """
    session = _manager.get(workflow_execution_id)
    if session is None:
        raise HTTPException(
            status_code=404,
            detail=f"Workflow execution '{workflow_execution_id}' not found",
        )
    if session.mode == WorkflowMode.FULL_NO_SSE:
        raise HTTPException(
            status_code=400,
            detail="SSE streaming is not available for FULL_NO_SSE executions",
        )

    q = session.add_subscriber()
    log.info(
        "SSE subscriber connected  workflow_execution_id=%s", workflow_execution_id
    )

    async def _heartbeat(queue: asyncio.Queue[str]) -> None:
        """Push SSE comment lines (keep-alive) into the subscriber queue."""
        while True:
            await asyncio.sleep(HEARTBEAT_INTERVAL)
            ts = datetime.now(timezone.utc).isoformat()
            try:
                queue.put_nowait(f": heartbeat {ts}\n\n")
            except asyncio.QueueFull:
                pass  # drop heartbeat if queue is full

    _TERMINAL_EVENTS = frozenset({"workflow_completed", "workflow_failed"})

    async def _event_generator() -> AsyncGenerator[str, None]:
        # Handshake – immediately confirms the stream is open
        yield _sse_format(
            "connected",
            {
                "workflow_execution_id": workflow_execution_id,
                "mode": session.mode,
                "message": "SSE stream open",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )

        heartbeat_task = asyncio.create_task(_heartbeat(q))
        terminal_seen = False
        try:
            while True:
                # Client disconnect check (Starlette ASGI)
                if await request.is_disconnected():
                    log.info(
                        "SSE client disconnected (detected)  workflow_execution_id=%s",
                        workflow_execution_id,
                    )
                    break

                # Drain remaining messages when the workflow has ended
                if terminal_seen and q.empty():
                    break

                try:
                    msg = await asyncio.wait_for(q.get(), timeout=1.0)
                except asyncio.TimeoutError:
                    continue

                yield msg

                # Track whether a terminal event has been delivered
                if any(f"event:{ev}" in msg for ev in _TERMINAL_EVENTS):
                    terminal_seen = True

        finally:
            heartbeat_task.cancel()
            session.remove_subscriber(q)
            log.info(
                "SSE subscriber removed  workflow_execution_id=%s",
                workflow_execution_id,
            )

    return StreamingResponse(
        _event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",   # disable nginx proxy buffering
            "Connection": "keep-alive",
        },
    )


# ── Entry point ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    uvicorn.run(
        "server:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="info",
        access_log=True,
    )
