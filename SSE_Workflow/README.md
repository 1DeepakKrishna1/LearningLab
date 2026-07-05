# SSE Workflow

A production-quality **Server-Sent Events (SSE) + REST API** system for long-running workflows.
The server runs a 10-step workflow and offers three execution modes. Clients can be written in
Python or Node.js and behave identically.

---

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Workflow Modes](#workflow-modes)
- [Project Structure](#project-structure)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Running the Server](#running-the-server)
- [Running the Python Client](#running-the-python-client)
- [Running the Node.js Client](#running-the-nodejs-client)
- [Multiple Concurrent Clients](#multiple-concurrent-clients)
- [API Reference](#api-reference)
- [SSE Event Catalog](#sse-event-catalog)
- [Configuration](#configuration)

---

## Overview

Each workflow is a **10-step long-running job**. Every step simulates 1 second of work and produces
a result. Three execution modes control how the client and server interact:

| Mode | How it works |
|---|---|
| `FULL_NO_SSE` | Single blocking HTTP call; server runs all steps silently and returns when done |
| `FULL_WITH_SSE` | Server starts the workflow in the background; client subscribes to an SSE stream and receives a live event per step |
| `STEP_MODE` | Server pauses after every step and sends an SSE event; client must call the resume endpoint to continue |

Multiple independent clients can run concurrently. Each receives its own unique
`workflow_execution_id` so their executions never interfere.

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                        Client                           │
│  (client.py  or  client.js)                             │
│                                                         │
│  1. POST /workflow/start  ─────────────────────────────►│
│  2. GET  /events/{id}     (SSE stream, modes 2 & 3) ───►│
│  3. POST /workflow/{id}/resume  (STEP_MODE only)   ────►│
│  4. GET  /workflow/{id}/status  (poll results)     ────►│
└────────────────────┬────────────────────────────────────┘
                     │  HTTP / SSE
┌────────────────────▼────────────────────────────────────┐
│                      server.py                          │
│  FastAPI + Uvicorn (ASGI)                               │
│                                                         │
│  SessionManager                                         │
│  └─ WorkflowSession  (one per workflow_execution_id)    │
│     ├─ asyncio.Task  (background runner)                │
│     ├─ asyncio.Event (STEP_MODE resume gate)            │
│     └─ per-subscriber asyncio.Queue  (SSE fan-out)      │
│                                                         │
│  SSE heartbeat task  (15 s keep-alive comments)        │
└─────────────────────────────────────────────────────────┘
```

**Key design points:**

- Each `WorkflowSession` maintains a list of subscriber queues. Broadcasting an event means
  putting a formatted SSE string onto every queue simultaneously — zero coupling between the
  workflow runner and the number of listeners.
- `STEP_MODE` synchronisation is a plain `asyncio.Event`; the resume endpoint sets it and the
  workflow task waits on it with a 300 s timeout.
- The SSE endpoint itself is a `StreamingResponse` backed by an async generator that drains
  the subscriber queue and yields formatted SSE chunks.
- The Python client and Node.js client use their own incremental SSE parsers (no third-party
  SSE library) so reconnection logic and retry back-off are fully under application control.

---

## Workflow Modes

### FULL_NO_SSE

```
Client                          Server
  │── POST /workflow/start ────►│
  │   { mode: FULL_NO_SSE }     │  runs all 10 steps (silently)
  │◄─ 200 { status: completed } ┤
  │── GET /workflow/{id}/status ►│
  │◄─ 200 { results: [...] } ───┤
```

- The `POST /workflow/start` call **blocks** until all steps finish.
- Poll `/workflow/{id}/status` afterward to retrieve the results array.

### FULL_WITH_SSE

```
Client                          Server
  │── POST /workflow/start ────►│
  │◄─ 200 { workflow_execution_id } ─┤  background task starts
  │── GET /events/{id} ────────►│
  │◄─ event: connected ─────────┤
  │◄─ event: step_started ──────┤  (×10)
  │◄─ event: step_completed ────┤  (×10)
  │◄─ event: workflow_completed ┤
  │   (stream closes)           │
```

- The start call returns immediately with `workflow_execution_id`.
- The SSE stream delivers real-time progress; the client exits when it receives
  `workflow_completed` or `workflow_failed`.

### STEP_MODE

```
Client                              Server
  │── POST /workflow/start ────────►│
  │◄─ 200 { workflow_execution_id } ┤  background task starts
  │── GET /events/{id} ────────────►│
  │◄─ event: connected ─────────────┤
  │◄─ event: step_started ──────────┤  step 1
  │◄─ event: step_completed ─────────┤
  │◄─ event: awaiting_resume ────────┤  PAUSED
  │── POST /workflow/{id}/resume ───►│
  │◄─ event: step_started ──────────┤  step 2
  │    ... (repeated for steps 2–9) ...
  │◄─ event: workflow_completed ─────┤
```

- After each step (except the last) the server pauses and sends `awaiting_resume`.
- The client must POST `/workflow/{id}/resume` to advance to the next step.
- Use `--auto-resume` to skip manual interaction.
- Resume times out after **300 seconds** if not called.

---

## Project Structure

```
SSE_Workflow/
├── server.py        # FastAPI + Uvicorn server (all three modes)
├── client.py        # Async Python client (httpx)
├── client.js        # Node.js client (built-in fetch, no npm needed)
├── requirements.txt # Python dependencies
└── README.md
```

---

## Prerequisites

### Server & Python Client

- Python >= 3.11 (uses `match` statement and `asyncio.to_thread`)
- pip

### Node.js Client

- Node.js >= 18 (uses built-in `fetch` and `ReadableStream` async iteration)
- No npm packages required

---

## Installation

### 1. Clone / enter the project directory

```bash
cd SSE_Workflow
```

### 2. Create a virtual environment (recommended)

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate
```

### 3. Install Python dependencies

```bash
pip install -r requirements.txt
```

`requirements.txt` contains:
```
fastapi>=0.111.0
uvicorn[standard]>=0.29.0
httpx>=0.27.0
pydantic>=2.7.0
```

The Node.js client (`client.js`) needs no installation step.

---

## Running the Server

```bash
python server.py
```

The server starts on **http://localhost:8000**.

Useful URLs once running:

| URL | Description |
|---|---|
| http://localhost:8000/health | Liveness probe |
| http://localhost:8000/docs | Interactive Swagger UI |
| http://localhost:8000/redoc | ReDoc API docs |

Sample output:

```
2024-01-01T12:00:00 [INFO    ] sse_workflow.server: SSE Workflow Server starting up
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

---

## Running the Python Client

### FULL_NO_SSE — blocking, no events

```bash
python client.py --mode FULL_NO_SSE
```

Sample output:
```
2024-01-01T12:00:00 [INFO    ] sse_workflow.client: Server health: {'status': 'ok', ...}
2024-01-01T12:00:00 [INFO    ] sse_workflow.client: ============================================================
2024-01-01T12:00:00 [INFO    ] sse_workflow.client: [client-1] Mode: FULL_NO_SSE
2024-01-01T12:00:00 [INFO    ] sse_workflow.client: [client-1] Starting workflow – server will run all steps silently...
2024-01-01T12:00:10 [INFO    ] sse_workflow.client: [client-1] Workflow finished: status=COMPLETED  workflow_execution_id=...
2024-01-01T12:00:10 [INFO    ] sse_workflow.client: [client-1] Results: 10/10 steps completed
2024-01-01T12:00:10 [INFO    ] sse_workflow.client: [client-1]   Step  1: Step 1 completed successfully  data=...
...
```

### FULL_WITH_SSE — live progress events

```bash
python client.py --mode FULL_WITH_SSE
```

Sample output:
```
...
[client-1] [SSE] Connected to stream for execution abc123
[client-1] [SSE] ▶  Step 1/10 started
[client-1] [SSE] ✓  Step 1/10 completed — Step 1 completed successfully
[client-1] [SSE] ▶  Step 2/10 started
...
[client-1] [SSE] *** WORKFLOW COMPLETED – 10 steps done ***
```

### STEP_MODE — interactive, manual resume

```bash
python client.py --mode STEP_MODE
```

After each step the client waits for ENTER:
```
[client-1] [SSE] ⏸  PAUSED after step 1/10 — waiting for resume
[client-1]        Resume URL: POST /workflow/abc123/resume

  >>> [client-1] Press ENTER to resume step 2 (or Ctrl-C to abort)...
```

### STEP_MODE — non-interactive auto resume

```bash
python client.py --mode STEP_MODE --auto-resume
```

### Remote server

```bash
python client.py --mode FULL_WITH_SSE --server http://remote-host:8000
```

---

## Running the Node.js Client

All commands mirror the Python client exactly.

### FULL_NO_SSE

```bash
node client.js --mode FULL_NO_SSE
```

### FULL_WITH_SSE

```bash
node client.js --mode FULL_WITH_SSE
```

### STEP_MODE — interactive

```bash
node client.js --mode STEP_MODE
```

### STEP_MODE — auto resume

```bash
node client.js --mode STEP_MODE --auto-resume
```

### Remote server

```bash
node client.js --mode FULL_WITH_SSE --server http://remote-host:8000
```

---

## Multiple Concurrent Clients

Both clients support `--clients N`. Each spawned client starts its **own independent workflow**
and receives a unique `workflow_execution_id`. Clients run concurrently; if one fails the others
continue to completion.

```bash
# Python – 3 concurrent FULL_WITH_SSE clients
python client.py --mode FULL_WITH_SSE --clients 3

# Node.js – 5 concurrent FULL_NO_SSE clients
node client.js --mode FULL_NO_SSE --clients 5

# Python – 2 concurrent STEP_MODE clients (auto-resume)
python client.py --mode STEP_MODE --auto-resume --clients 2

# Node.js – same
node client.js --mode STEP_MODE --auto-resume --clients 2
```

> **Note:** Interactive `STEP_MODE` (without `--auto-resume`) with `--clients > 1` is supported
> but will prompt for ENTER once per client per step — use `--auto-resume` for multi-client
> STEP_MODE runs.

---

## API Reference

### `GET /health`

Liveness probe.

**Response `200`:**
```json
{
  "status": "ok",
  "active_executions": 2,
  "timestamp": "2024-01-01T12:00:00+00:00"
}
```

---

### `POST /workflow/start`

Start a new workflow execution.

**Request body:**
```json
{ "mode": "FULL_NO_SSE" }
```

`mode` must be one of `FULL_NO_SSE`, `FULL_WITH_SSE`, `STEP_MODE`.

**Response `200`:**
```json
{
  "workflow_execution_id": "550e8400-e29b-41d4-a716-446655440000",
  "mode": "FULL_WITH_SSE",
  "status": "PENDING",
  "message": "Workflow started in background. Connect to GET /events/... for live updates."
}
```

For `FULL_NO_SSE` the call **blocks** until all steps complete and returns `status: COMPLETED`.

---

### `GET /events/{workflow_execution_id}`

Long-lived SSE stream. Not available for `FULL_NO_SSE` executions (returns `400`).

**Headers returned:**
```
Content-Type: text/event-stream
Cache-Control: no-cache
Connection: keep-alive
X-Accel-Buffering: no
```

Multiple clients may subscribe to the same `workflow_execution_id` simultaneously; each
receives an independent copy of every event.

---

### `POST /workflow/{workflow_execution_id}/resume`

Advance a `STEP_MODE` workflow that is paused. Returns `409` if the execution is not paused.

**Response `200`:**
```json
{
  "workflow_execution_id": "550e8400-...",
  "resumed_from_step": 3,
  "status": "RUNNING",
  "message": "Resumed from step 3; step 4 will begin shortly."
}
```

---

### `GET /workflow/{workflow_execution_id}/status`

Poll current status and accumulated step results.

**Response `200`:**
```json
{
  "workflow_execution_id": "550e8400-...",
  "mode": "FULL_NO_SSE",
  "status": "COMPLETED",
  "current_step": 10,
  "total_steps": 10,
  "results": [
    {
      "step": 1,
      "status": "completed",
      "message": "Step 1 completed successfully",
      "timestamp": "2024-01-01T12:00:01+00:00",
      "data": { "output": "result_step_1", "processed_items": 100 }
    }
  ],
  "error": null
}
```

`status` values: `PENDING` | `RUNNING` | `PAUSED` | `COMPLETED` | `FAILED`

---

## SSE Event Catalog

All events carry a JSON `data` payload. The `retry:3000` field instructs the browser
`EventSource` to wait 3 seconds before reconnecting if the connection drops.

| Event | When emitted | Key payload fields |
|---|---|---|
| `connected` | Immediately on SSE connection open | `workflow_execution_id`, `mode` |
| `step_started` | Before each step begins | `step`, `total`, `message`, `timestamp` |
| `step_completed` | After each step finishes | `step`, `total`, `message`, `data`, `timestamp` |
| `awaiting_resume` | After each step in STEP_MODE (except the last) | `step`, `next_step`, `total`, `resume_url`, `timestamp` |
| `workflow_completed` | All steps done | `total_steps`, `results_count`, `timestamp` |
| `workflow_failed` | Unrecoverable error or cancellation | `message`, `timestamp` |
| *(SSE comment)* | Every 15 s | Heartbeat — invisible to `EventSource`, keeps proxies alive |

**Example raw SSE event:**
```
retry:3000
event:step_completed
data:{"workflow_execution_id":"550e8400-...","step":3,"total":10,"message":"Step 3 completed successfully","data":{"output":"result_step_3","processed_items":300},"timestamp":"2024-01-01T12:00:03+00:00"}

```

---

## Configuration

All tuneable constants live at the top of each file.

### Server (`server.py`)

| Constant | Default | Description |
|---|---|---|
| `TOTAL_STEPS` | `10` | Number of steps per workflow |
| `STEP_DURATION_SECONDS` | `1.0` | Simulated work time per step (seconds) |
| `HEARTBEAT_INTERVAL` | `15.0` | SSE keep-alive comment interval (seconds) |
| `SSE_RETRY_MS` | `3000` | `retry:` hint sent to SSE clients (ms) |
| `STEP_MODE_RESUME_TIMEOUT` | `300.0` | Max wait for a resume call before failing (seconds) |

### Python Client (`client.py`)

| Constant | Default | Description |
|---|---|---|
| `DEFAULT_SERVER` | `http://localhost:8000` | Server base URL |
| `REST_TIMEOUT` | `180.0` | Timeout for blocking REST calls (seconds) |
| `MAX_SSE_RETRIES` | `5` | Max reconnection attempts on SSE error |
| `SSE_RETRY_BACKOFF` | `[1,2,4,8,16]` | Exponential back-off delays (seconds) |

### Node.js Client (`client.js`)

| Constant | Default | Description |
|---|---|---|
| `DEFAULT_SERVER` | `http://localhost:8000` | Server base URL |
| `REST_TIMEOUT_MS` | `180000` | Timeout for blocking REST calls (ms) |
| `MAX_SSE_RETRIES` | `5` | Max reconnection attempts on SSE error |
| `SSE_RETRY_BACKOFF` | `[1,2,4,8,16]` | Exponential back-off delays (seconds) |
