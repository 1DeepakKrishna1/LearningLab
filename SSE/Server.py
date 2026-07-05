"""
Production-ready Python Server-Sent Events (SSE) + REST API system

Stack:
- FastAPI (server)
- Uvicorn (ASGI server)
- httpx (client REST)
- sseclient-py (client SSE)
- asyncio queue for event streaming

Features:
- REST endpoint to trigger events
- SSE endpoint to stream events to clients
- Multi-client support
- Heartbeat
- Graceful disconnect handling
- Typed models
- Logging
- Retry support
"""

# ========================= SERVER =========================

import asyncio
import json
import logging
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Dict, List

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("sse_server")

app = FastAPI()

# In-memory client registry
clients: Dict[str, asyncio.Queue] = {}

class EventRequest(BaseModel):
    client_id: str
    message: str


async def event_generator(client_id: str):
    """Streams events for a specific client"""
    queue = clients.get(client_id)
    if not queue:
        queue = asyncio.Queue()
        clients[client_id] = queue

    try:
        while True:
            try:
                data = await asyncio.wait_for(queue.get(), timeout=15)
                yield f"data: {json.dumps(data)}\n\n"
            except asyncio.TimeoutError:
                # Heartbeat to keep connection alive
                yield "event: heartbeat\ndata: ping\n\n"
    except asyncio.CancelledError:
        logger.info(f"Client {client_id} disconnected")
        clients.pop(client_id, None)


@app.get("/sse/{client_id}")
async def sse_endpoint(request: Request, client_id: str):
    """SSE endpoint for clients"""
    logger.info(f"Client connected: {client_id}")

    async def generator():
        async for event in event_generator(client_id):
            if await request.is_disconnected():
                logger.info(f"Client {client_id} disconnected via request")
                break
            yield event

    return StreamingResponse(generator(), media_type="text/event-stream")


@app.post("/send")
async def send_event(req: EventRequest):
    """REST API to send event to a client"""
    if req.client_id not in clients:
        return {"status": "error", "message": "Client not connected"}

    await clients[req.client_id].put({
        "message": req.message,
        "timestamp": asyncio.get_event_loop().time()
    })

    return {"status": "sent"}


@app.get("/health")
async def health():
    return {"status": "ok"}


# ========================= CLIENT =========================

import threading
import httpx
import time

try:
    from sseclient import SSEClient
except ImportError:
    SSEClient = None


SERVER_URL = "http://localhost:8000"
CLIENT_ID = "client-1"


def listen_sse():
    """Listen to SSE stream"""
    if not SSEClient:
        print("Install sseclient-py: pip install sseclient-py")
        return

    url = f"{SERVER_URL}/sse/{CLIENT_ID}"
    print(f"Connecting to SSE: {url}")

    messages = SSEClient(url)

    for msg in messages:
        if msg.event == "heartbeat":
            print("[Heartbeat]")
        else:
            print(f"[Event] {msg.data}")


def send_message(msg: str):
    """Send message via REST"""
    with httpx.Client() as client:
        response = client.post(f"{SERVER_URL}/send", json={
            "client_id": CLIENT_ID,
            "message": msg
        })
        print("Response:", response.json())


if __name__ == "__main__":
    # Start SSE listener in background
    thread = threading.Thread(target=listen_sse, daemon=True)
    thread.start()

    time.sleep(2)

    # Send test messages
    for i in range(5):
        send_message(f"Hello {i}")
        time.sleep(2)


# ========================= RUN =========================

# 1. Install dependencies:
# pip install fastapi uvicorn httpx sseclient-py

# 2. Start server:
# uvicorn filename:app --reload

# 3. Run client:
# python filename.py

# ========================= ADVANCED WORKFLOW EXECUTION =========================

"""
This section adds:
1. 10-step long running workflow
2. Modes:
   - FULL_NO_SSE (silent execution)
   - FULL_WITH_SSE (continuous progress updates)
   - STEP_MODE (pause after each step, wait for resume)
3. Resume API
"""

from enum import Enum

class ExecutionMode(str, Enum):
    FULL_NO_SSE = "full_no_sse"
    FULL_WITH_SSE = "full_with_sse"
    STEP_MODE = "step_mode"

# Track workflow state
workflow_state: Dict[str, Dict] = {}


async def run_workflow(client_id: str, mode: ExecutionMode):
    steps = [f"Step-{i}" for i in range(1, 11)]

    workflow_state[client_id] = {
        "current_step": 0,
        "paused": False,
        "mode": mode
    }

    for idx, step in enumerate(steps):
        workflow_state[client_id]["current_step"] = idx

        # Simulate processing
        await asyncio.sleep(2)

        # Send SSE update if required
        if mode != ExecutionMode.FULL_NO_SSE and client_id in clients:
            await clients[client_id].put({
                "type": "progress",
                "step": step,
                "step_number": idx + 1
            })

        # STEP MODE: pause after each step
        if mode == ExecutionMode.STEP_MODE:
            workflow_state[client_id]["paused"] = True

            if client_id in clients:
                await clients[client_id].put({
                    "type": "pause",
                    "message": f"Paused at {step}. Call resume API to continue."
                })

            # Wait until resume
            while workflow_state[client_id]["paused"]:
                await asyncio.sleep(1)

    # Completion
    if mode != ExecutionMode.FULL_NO_SSE and client_id in clients:
        await clients[client_id].put({
            "type": "complete",
            "message": "Workflow completed"
        })


@app.post("/start_workflow")
async def start_workflow(req: EventRequest, mode: ExecutionMode):
    """Start workflow in background"""
    asyncio.create_task(run_workflow(req.client_id, mode))
    return {"status": "started", "mode": mode}


@app.post("/resume/{client_id}")
async def resume_workflow(client_id: str):
    """Resume paused workflow"""
    if client_id not in workflow_state:
        return {"status": "error", "message": "No workflow found"}

    workflow_state[client_id]["paused"] = False

    if client_id in clients:
        await clients[client_id].put({
            "type": "resume",
            "message": "Resuming workflow"
        })

    return {"status": "resumed"}