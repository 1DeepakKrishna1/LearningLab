"""
SSE Workflow Client
===================
Async Python client (httpx) that exercises all three server workflow modes.
Supports running multiple concurrent clients, each with its own independent
workflow_execution_id.

  FULL_NO_SSE   – fire a single blocking request; poll status for results
  FULL_WITH_SSE – start workflow, subscribe to SSE stream for live progress
  STEP_MODE     – start workflow, receive pause events, send resume calls

Usage
-----
  # Single client
  python client.py --mode FULL_NO_SSE
  python client.py --mode FULL_WITH_SSE
  python client.py --mode STEP_MODE --auto-resume      # non-interactive
  python client.py --mode STEP_MODE                    # interactive (press ENTER)

  # Multiple concurrent clients (each gets its own workflow_execution_id)
  python client.py --mode FULL_WITH_SSE --clients 3
  python client.py --mode FULL_NO_SSE --clients 5
  python client.py --mode STEP_MODE --auto-resume --clients 2

  # Remote server
  python client.py --mode FULL_WITH_SSE --server http://remote-host:8000
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Coroutine, List, Optional

import httpx

# ── Logging ────────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)-8s] %(name)s: %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
log = logging.getLogger("sse_workflow.client")

# ── Config defaults ────────────────────────────────────────────────────────────

DEFAULT_SERVER = "http://localhost:8000"
SSE_READ_TIMEOUT = None          # infinite (stream is long-lived)
REST_TIMEOUT = 180.0             # FULL_NO_SSE blocks the full workflow duration
MAX_SSE_RETRIES = 5
SSE_RETRY_BACKOFF = [1, 2, 4, 8, 16]  # seconds


class WorkflowMode(str, Enum):
    FULL_NO_SSE = "FULL_NO_SSE"
    FULL_WITH_SSE = "FULL_WITH_SSE"
    STEP_MODE = "STEP_MODE"


# ── SSE event parser ───────────────────────────────────────────────────────────

@dataclass
class SSEEvent:
    event: str = "message"
    data: str = ""
    retry: Optional[int] = None

    def json(self) -> dict:
        """Deserialise the data field as JSON; fall back to a raw wrapper."""
        try:
            return json.loads(self.data)
        except (json.JSONDecodeError, ValueError):
            return {"raw": self.data}


class _SSEParser:
    """
    Incremental SSE parser. Feed raw text chunks via ``feed()``; retrieve
    complete events via ``events()``.
    """

    def __init__(self) -> None:
        self._buf = ""
        self._ready: List[SSEEvent] = []

    def feed(self, chunk: str) -> None:
        self._buf += chunk
        while "\n\n" in self._buf:
            raw_event, self._buf = self._buf.split("\n\n", 1)
            ev = self._parse_block(raw_event)
            if ev is not None:
                self._ready.append(ev)

    def events(self) -> List[SSEEvent]:
        out, self._ready = self._ready, []
        return out

    @staticmethod
    def _parse_block(block: str) -> Optional[SSEEvent]:
        ev = SSEEvent()
        data_lines: List[str] = []
        for line in block.splitlines():
            if line.startswith("event:"):
                ev.event = line[6:].strip()
            elif line.startswith("data:"):
                data_lines.append(line[5:].strip())
            elif line.startswith("retry:"):
                try:
                    ev.retry = int(line[6:].strip())
                except ValueError:
                    pass
            # Lines starting with ':' are SSE comments (heartbeats) – ignore.
        if not data_lines:
            return None  # comment-only block, not a real event
        ev.data = "\n".join(data_lines)
        return ev


# ── SSE stream consumer ────────────────────────────────────────────────────────

EventHandler = Callable[[SSEEvent], Coroutine[Any, Any, None]]

_TERMINAL_EVENTS = frozenset({"workflow_completed", "workflow_failed"})


async def consume_sse(
    client: httpx.AsyncClient,
    server: str,
    workflow_execution_id: str,
    on_event: EventHandler,
) -> None:
    """
    Open a persistent SSE connection to ``GET /events/{workflow_execution_id}`` and
    call *on_event* for every event received. Returns when a terminal event is seen
    or the server closes the connection.

    Implements automatic reconnection with exponential back-off.
    """
    url = f"{server}/events/{workflow_execution_id}"
    parser = _SSEParser()
    attempt = 0

    while True:
        try:
            log.info("Connecting to SSE stream %s (attempt %d)", url, attempt + 1)
            async with client.stream(
                "GET",
                url,
                timeout=httpx.Timeout(
                    connect=10.0,
                    read=SSE_READ_TIMEOUT,
                    write=10.0,
                    pool=10.0,
                ),
            ) as resp:
                if resp.status_code != 200:
                    body = await resp.aread()
                    raise httpx.HTTPStatusError(
                        f"SSE endpoint returned {resp.status_code}: {body.decode()[:200]}",
                        request=resp.request,
                        response=resp,
                    )

                attempt = 0  # reset on successful connect
                terminal_seen = False

                async for chunk in resp.aiter_text():
                    parser.feed(chunk)
                    for ev in parser.events():
                        await on_event(ev)
                        if ev.event in _TERMINAL_EVENTS:
                            terminal_seen = True

                    if terminal_seen:
                        return  # clean exit

        except (httpx.RemoteProtocolError, httpx.ReadError, httpx.ConnectError) as exc:
            attempt += 1
            if attempt > MAX_SSE_RETRIES:
                log.error("SSE max retries (%d) exceeded – giving up", MAX_SSE_RETRIES)
                raise
            delay = SSE_RETRY_BACKOFF[min(attempt - 1, len(SSE_RETRY_BACKOFF) - 1)]
            log.warning(
                "SSE connection error (%s) – reconnecting in %ds (attempt %d/%d)",
                exc,
                delay,
                attempt,
                MAX_SSE_RETRIES,
            )
            await asyncio.sleep(delay)


# ── Mode implementations ───────────────────────────────────────────────────────

async def run_full_no_sse(
    client: httpx.AsyncClient, server: str, client_id: int = 1
) -> None:
    """
    FULL_NO_SSE – single blocking POST; all 10 steps execute server-side
    before the response is returned. Poll status endpoint for the results.
    """
    prefix = f"[client-{client_id}]"
    log.info("=" * 60)
    log.info("%s Mode: FULL_NO_SSE", prefix)
    log.info("%s Starting workflow – server will run all steps silently...", prefix)

    resp = await client.post(
        f"{server}/workflow/start",
        json={"mode": WorkflowMode.FULL_NO_SSE},
        timeout=REST_TIMEOUT,
    )
    resp.raise_for_status()
    data = resp.json()
    workflow_execution_id = data["workflow_execution_id"]

    log.info(
        "%s Workflow finished: status=%s  workflow_execution_id=%s",
        prefix,
        data["status"],
        workflow_execution_id,
    )

    # Retrieve full results via status endpoint
    status_resp = await client.get(
        f"{server}/workflow/{workflow_execution_id}/status",
        timeout=REST_TIMEOUT,
    )
    status_resp.raise_for_status()
    status = status_resp.json()

    log.info(
        "%s Results: %d/%d steps completed",
        prefix,
        len(status["results"]),
        status["total_steps"],
    )
    for r in status["results"]:
        log.info(
            "%s   Step %2d: %s  data=%s", prefix, r["step"], r["message"], r.get("data")
        )


async def run_full_with_sse(
    client: httpx.AsyncClient, server: str, client_id: int = 1
) -> None:
    """
    FULL_WITH_SSE – start workflow in background, subscribe to SSE stream
    and log every progress event as it arrives.
    """
    prefix = f"[client-{client_id}]"
    log.info("=" * 60)
    log.info("%s Mode: FULL_WITH_SSE", prefix)

    resp = await client.post(
        f"{server}/workflow/start",
        json={"mode": WorkflowMode.FULL_WITH_SSE},
        timeout=30.0,
    )
    resp.raise_for_status()
    data = resp.json()
    workflow_execution_id = data["workflow_execution_id"]
    log.info("%s Workflow started: workflow_execution_id=%s", prefix, workflow_execution_id)
    log.info("%s Subscribing to SSE stream for live progress...", prefix)

    async def on_event(ev: SSEEvent) -> None:
        payload = ev.json()
        match ev.event:
            case "connected":
                log.info(
                    "%s [SSE] Connected to stream for execution %s",
                    prefix,
                    workflow_execution_id,
                )
            case "step_started":
                log.info(
                    "%s [SSE] ▶  Step %s/%s started",
                    prefix,
                    payload.get("step"),
                    payload.get("total"),
                )
            case "step_completed":
                log.info(
                    "%s [SSE] ✓  Step %s/%s completed — %s",
                    prefix,
                    payload.get("step"),
                    payload.get("total"),
                    payload.get("message"),
                )
            case "workflow_completed":
                log.info(
                    "%s [SSE] *** WORKFLOW COMPLETED – %s steps done ***",
                    prefix,
                    payload.get("total_steps"),
                )
            case "workflow_failed":
                log.error(
                    "%s [SSE] ✗ WORKFLOW FAILED: %s", prefix, payload.get("message")
                )
            case _:
                log.debug(
                    "%s [SSE] event=%s  payload=%s", prefix, ev.event, payload
                )

    await consume_sse(client, server, workflow_execution_id, on_event)


async def run_step_mode(
    client: httpx.AsyncClient,
    server: str,
    auto_resume: bool = False,
    client_id: int = 1,
) -> None:
    """
    STEP_MODE – workflow pauses after each step and waits for an explicit
    resume call.  In interactive mode the user presses ENTER to continue;
    with ``--auto-resume`` the client resumes automatically.
    """
    prefix = f"[client-{client_id}]"
    log.info("=" * 60)
    log.info("%s Mode: STEP_MODE  (auto_resume=%s)", prefix, auto_resume)

    resp = await client.post(
        f"{server}/workflow/start",
        json={"mode": WorkflowMode.STEP_MODE},
        timeout=30.0,
    )
    resp.raise_for_status()
    data = resp.json()
    workflow_execution_id = data["workflow_execution_id"]
    log.info("%s Workflow started: workflow_execution_id=%s", prefix, workflow_execution_id)
    log.info("%s Subscribing to SSE stream...", prefix)

    async def _send_resume() -> None:
        """Call POST /workflow/{workflow_execution_id}/resume and log the outcome."""
        resume_resp = await client.post(
            f"{server}/workflow/{workflow_execution_id}/resume",
            timeout=30.0,
        )
        resume_resp.raise_for_status()
        body = resume_resp.json()
        log.info(
            "%s [CLIENT] Resume accepted: %s  (next step coming up...)",
            prefix,
            body.get("message"),
        )

    async def on_event(ev: SSEEvent) -> None:
        payload = ev.json()
        match ev.event:
            case "connected":
                log.info(
                    "%s [SSE] Connected to stream for execution %s",
                    prefix,
                    workflow_execution_id,
                )
            case "step_started":
                log.info(
                    "%s [SSE] ▶  Step %s/%s started",
                    prefix,
                    payload.get("step"),
                    payload.get("total"),
                )
            case "step_completed":
                log.info(
                    "%s [SSE] ✓  Step %s/%s completed",
                    prefix,
                    payload.get("step"),
                    payload.get("total"),
                )
            case "awaiting_resume":
                step = payload.get("step")
                next_step = payload.get("next_step")
                log.info(
                    "%s [SSE] ⏸  PAUSED after step %s/%s — waiting for resume",
                    prefix,
                    step,
                    payload.get("total"),
                )
                log.info(
                    "%s        Resume URL: POST %s", prefix, payload.get("resume_url")
                )

                if auto_resume:
                    await asyncio.sleep(0.5)  # brief visual pause
                    log.info(
                        "%s [CLIENT] Auto-resuming to step %s...", prefix, next_step
                    )
                    await _send_resume()
                else:
                    # Interactive: block the event loop on stdin in a thread
                    # so we don't starve the asyncio scheduler.
                    await asyncio.to_thread(
                        input,
                        f"\n  >>> [{prefix}] Press ENTER to resume step {next_step} "
                        f"(or Ctrl-C to abort)...\n",
                    )
                    await _send_resume()

            case "workflow_completed":
                log.info(
                    "%s [SSE] *** WORKFLOW COMPLETED – %s steps done ***",
                    prefix,
                    payload.get("total_steps"),
                )
            case "workflow_failed":
                log.error(
                    "%s [SSE] ✗ WORKFLOW FAILED: %s", prefix, payload.get("message")
                )
            case _:
                log.debug(
                    "%s [SSE] event=%s  payload=%s", prefix, ev.event, payload
                )

    await consume_sse(client, server, workflow_execution_id, on_event)


# ── CLI entry point ────────────────────────────────────────────────────────────

def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description=(
            "SSE Workflow Client – exercises all three server workflow modes. "
            "Supports launching multiple concurrent clients, each identified by "
            "its own workflow_execution_id."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument(
        "--mode",
        choices=[m.value for m in WorkflowMode],
        required=True,
        metavar="MODE",
        help="Workflow execution mode: FULL_NO_SSE | FULL_WITH_SSE | STEP_MODE",
    )
    p.add_argument(
        "--auto-resume",
        action="store_true",
        default=False,
        help="(STEP_MODE only) Automatically send resume after each step",
    )
    p.add_argument(
        "--server",
        default=DEFAULT_SERVER,
        metavar="URL",
        help=f"Server base URL (default: {DEFAULT_SERVER})",
    )
    p.add_argument(
        "--clients",
        type=int,
        default=1,
        metavar="N",
        help=(
            "Number of concurrent clients to run (default: 1). Each client starts "
            "its own independent workflow and receives a unique workflow_execution_id."
        ),
    )
    return p


async def _main(args: argparse.Namespace) -> None:
    server = args.server.rstrip("/")
    mode = WorkflowMode(args.mode)
    num_clients = max(1, args.clients)

    # Shared async client – connection pooling, keep-alive, etc.
    # Scale pool size to accommodate multiple concurrent SSE streams.
    limits = httpx.Limits(
        max_connections=num_clients * 4,
        max_keepalive_connections=num_clients * 2,
    )
    async with httpx.AsyncClient(limits=limits) as client:
        # Verify server is reachable before starting
        try:
            health = await client.get(f"{server}/health", timeout=5.0)
            health.raise_for_status()
            log.info("Server health: %s", health.json())
        except Exception as exc:
            log.error("Cannot reach server at %s – %s", server, exc)
            sys.exit(1)

        if num_clients == 1:
            # Single-client path – same behaviour as before
            match mode:
                case WorkflowMode.FULL_NO_SSE:
                    await run_full_no_sse(client, server, client_id=1)
                case WorkflowMode.FULL_WITH_SSE:
                    await run_full_with_sse(client, server, client_id=1)
                case WorkflowMode.STEP_MODE:
                    await run_step_mode(
                        client, server, auto_resume=args.auto_resume, client_id=1
                    )
        else:
            # Multi-client path – launch N concurrent workflow executions.
            # Each gets its own workflow_execution_id from the server.
            log.info(
                "Launching %d concurrent clients in mode=%s", num_clients, mode
            )

            async def _run_client(client_id: int) -> None:
                match mode:
                    case WorkflowMode.FULL_NO_SSE:
                        await run_full_no_sse(client, server, client_id=client_id)
                    case WorkflowMode.FULL_WITH_SSE:
                        await run_full_with_sse(client, server, client_id=client_id)
                    case WorkflowMode.STEP_MODE:
                        await run_step_mode(
                            client,
                            server,
                            auto_resume=args.auto_resume,
                            client_id=client_id,
                        )

            # asyncio.gather runs all coroutines concurrently; return_exceptions
            # ensures one failure does not abort the others.
            results = await asyncio.gather(
                *[_run_client(i + 1) for i in range(num_clients)],
                return_exceptions=True,
            )

            # Report any per-client failures
            for idx, result in enumerate(results, start=1):
                if isinstance(result, Exception):
                    log.error(
                        "client-%d raised an exception: %s", idx, result
                    )

            log.info("All %d clients finished.", num_clients)


def main() -> None:
    args = _build_parser().parse_args()
    try:
        asyncio.run(_main(args))
    except KeyboardInterrupt:
        log.info("Client interrupted by user")
        sys.exit(0)


if __name__ == "__main__":
    main()
