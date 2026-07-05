#!/usr/bin/env node
/**
 * SSE Workflow Client (Node.js)
 * ==============================
 * Built-in-only Node.js client (>= 18) that exercises all three server workflow modes.
 * Supports running multiple concurrent clients, each with its own independent
 * workflow_execution_id.
 *
 *   FULL_NO_SSE   – fire a single blocking request; poll status for results
 *   FULL_WITH_SSE – start workflow, subscribe to SSE stream for live progress
 *   STEP_MODE     – start workflow, receive pause events, send resume calls
 *
 * Usage
 * -----
 *   # Single client
 *   node client.js --mode FULL_NO_SSE
 *   node client.js --mode FULL_WITH_SSE
 *   node client.js --mode STEP_MODE --auto-resume      # non-interactive
 *   node client.js --mode STEP_MODE                    # interactive (press ENTER)
 *
 *   # Multiple concurrent clients (each gets its own workflow_execution_id)
 *   node client.js --mode FULL_WITH_SSE --clients 3
 *   node client.js --mode FULL_NO_SSE --clients 5
 *   node client.js --mode STEP_MODE --auto-resume --clients 2
 *
 *   # Remote server
 *   node client.js --mode FULL_WITH_SSE --server http://remote-host:8000
 *
 * Requirements: Node.js >= 18 (built-in fetch, ReadableStream, TextDecoder)
 */

'use strict';

const readline = require('readline');

// ── Config defaults ────────────────────────────────────────────────────────────

//const DEFAULT_SERVER = 'http://localhost:8000';
const DEFAULT_SERVER = "http://127.0.0.1:8000"
const REST_TIMEOUT_MS = 180_000;            // 180 s – FULL_NO_SSE blocks the full workflow
const MAX_SSE_RETRIES = 5;
const SSE_RETRY_BACKOFF = [1, 2, 4, 8, 16]; // seconds

// ── Logging ────────────────────────────────────────────────────────────────────

function _ts() {
  // Matches Python's datefmt="%Y-%m-%dT%H:%M:%S"
  return new Date().toISOString().slice(0, 19);
}

const log = {
  info:  (...a) => console.log (`${_ts()} [INFO    ] sse_workflow.client:`, ...a),
  warn:  (...a) => console.warn(`${_ts()} [WARNING ] sse_workflow.client:`, ...a),
  error: (...a) => console.error(`${_ts()} [ERROR   ] sse_workflow.client:`, ...a),
  debug: (...a) => { if (process.env.DEBUG) console.debug(`${_ts()} [DEBUG   ] sse_workflow.client:`, ...a); },
};

// ── SSE event parser ───────────────────────────────────────────────────────────

class SSEParser {
  constructor() {
    this._buf = '';
    this._ready = [];
  }

  feed(chunk) {
    this._buf += chunk;
    while (this._buf.includes('\n\n')) {
      const idx = this._buf.indexOf('\n\n');
      const rawEvent = this._buf.slice(0, idx);
      this._buf = this._buf.slice(idx + 2);
      const ev = this._parseBlock(rawEvent);
      if (ev !== null) this._ready.push(ev);
    }
  }

  events() {
    const out = this._ready;
    this._ready = [];
    return out;
  }

  _parseBlock(block) {
    const ev = { event: 'message', data: '', retry: null };
    const dataLines = [];
    for (const line of block.split('\n')) {
      if (line.startsWith('event:')) {
        ev.event = line.slice(6).trim();
      } else if (line.startsWith('data:')) {
        dataLines.push(line.slice(5).trim());
      } else if (line.startsWith('retry:')) {
        const n = parseInt(line.slice(6).trim(), 10);
        if (!isNaN(n)) ev.retry = n;
      }
      // Lines starting with ':' are SSE comments (heartbeats) – ignore.
    }
    if (dataLines.length === 0) return null; // comment-only block
    ev.data = dataLines.join('\n');
    return ev;
  }
}

function parseSSEJson(ev) {
  try {
    return JSON.parse(ev.data);
  } catch {
    return { raw: ev.data };
  }
}

// ── SSE stream consumer ────────────────────────────────────────────────────────

const TERMINAL_EVENTS = new Set(['workflow_completed', 'workflow_failed']);

/**
 * Open a persistent SSE connection to GET /events/{workflow_execution_id} and
 * call onEvent for every event received. Returns when a terminal event is seen
 * or the server closes the connection.
 *
 * Implements automatic reconnection with exponential back-off.
 *
 * @param {string} server
 * @param {string} workflowExecutionId
 * @param {(ev: {event: string, data: string, retry: number|null}) => Promise<void>} onEvent
 */
async function consumeSSE(server, workflowExecutionId, onEvent) {
  const url = `${server}/events/${workflowExecutionId}`;
  const parser = new SSEParser();
  let attempt = 0;

  while (true) {
    const controller = new AbortController();
    try {
      log.info(`Connecting to SSE stream ${url} (attempt ${attempt + 1})`);

      const resp = await fetch(url, {
        signal: controller.signal,
        headers: { Accept: 'text/event-stream' },
      });

      if (!resp.ok) {
        const body = await resp.text();
        throw new Error(`SSE endpoint returned ${resp.status}: ${body.slice(0, 200)}`);
      }

      attempt = 0; // reset on successful connect
      let terminalSeen = false;
      const decoder = new TextDecoder();

      for await (const chunk of resp.body) {
        parser.feed(decoder.decode(chunk, { stream: true }));
        for (const ev of parser.events()) {
          await onEvent(ev);
          if (TERMINAL_EVENTS.has(ev.event)) terminalSeen = true;
        }
        if (terminalSeen) {
          controller.abort();
          return; // clean exit after terminal event
        }
      }

      if (terminalSeen) return;

    } catch (err) {
      if (err.name === 'AbortError') return; // intentional abort – clean exit

      attempt++;
      if (attempt > MAX_SSE_RETRIES) {
        log.error(`SSE max retries (${MAX_SSE_RETRIES}) exceeded – giving up`);
        throw err;
      }
      const delay = SSE_RETRY_BACKOFF[Math.min(attempt - 1, SSE_RETRY_BACKOFF.length - 1)];
      log.warn(
        `SSE connection error (${err.message}) – reconnecting in ${delay}s ` +
        `(attempt ${attempt}/${MAX_SSE_RETRIES})`
      );
      await sleep(delay * 1000);
    }
  }
}

// ── HTTP helpers ───────────────────────────────────────────────────────────────

function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

/**
 * fetch wrapper that throws on non-2xx and returns parsed JSON.
 * Respects an optional timeout (ms).
 */
async function fetchJSON(url, { timeout = REST_TIMEOUT_MS, ...opts } = {}) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeout);
  try {
    const resp = await fetch(url, { ...opts, signal: controller.signal });
    if (!resp.ok) {
      const body = await resp.text();
      throw new Error(`HTTP ${resp.status}: ${body.slice(0, 200)}`);
    }
    return resp.json();
  } finally {
    clearTimeout(timer);
  }
}

/** Block until the user presses ENTER (runs in async context without blocking event loop). */
function promptEnter(message) {
  return new Promise(resolve => {
    // Use a fresh interface each time so concurrent callers don't conflict.
    const rl = readline.createInterface({ input: process.stdin, output: process.stdout });
    rl.question(message, () => {
      rl.close();
      resolve();
    });
  });
}

// ── Mode implementations ───────────────────────────────────────────────────────

/**
 * FULL_NO_SSE – single blocking POST; all 10 steps execute server-side
 * before the response is returned. Poll status endpoint for the results.
 */
async function runFullNoSSE(server, clientId = 1) {
  const prefix = `[client-${clientId}]`;
  log.info('='.repeat(60));
  log.info(`${prefix} Mode: FULL_NO_SSE`);
  log.info(`${prefix} Starting workflow – server will run all steps silently...`);

  const data = await fetchJSON(`${server}/workflow/start`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ mode: 'FULL_NO_SSE' }),
    timeout: REST_TIMEOUT_MS,
  });

  const { workflow_execution_id } = data;
  log.info(
    `${prefix} Workflow finished: status=${data.status}  workflow_execution_id=${workflow_execution_id}`
  );

  // Retrieve full results via status endpoint
  const status = await fetchJSON(
    `${server}/workflow/${workflow_execution_id}/status`,
    { timeout: REST_TIMEOUT_MS }
  );

  log.info(`${prefix} Results: ${status.results.length}/${status.total_steps} steps completed`);
  for (const r of status.results) {
    log.info(
      `${prefix}   Step ${String(r.step).padStart(2)}: ${r.message}  data=${JSON.stringify(r.data)}`
    );
  }
}

/**
 * FULL_WITH_SSE – start workflow in background, subscribe to SSE stream
 * and log every progress event as it arrives.
 */
async function runFullWithSSE(server, clientId = 1) {
  const prefix = `[client-${clientId}]`;
  log.info('='.repeat(60));
  log.info(`${prefix} Mode: FULL_WITH_SSE`);

  const data = await fetchJSON(`${server}/workflow/start`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ mode: 'FULL_WITH_SSE' }),
    timeout: 30_000,
  });

  const { workflow_execution_id } = data;
  log.info(`${prefix} Workflow started: workflow_execution_id=${workflow_execution_id}`);
  log.info(`${prefix} Subscribing to SSE stream for live progress...`);

  await consumeSSE(server, workflow_execution_id, async (ev) => {
    const payload = parseSSEJson(ev);
    switch (ev.event) {
      case 'connected':
        log.info(`${prefix} [SSE] Connected to stream for execution ${workflow_execution_id}`);
        break;
      case 'step_started':
        log.info(`${prefix} [SSE] \u25b6  Step ${payload.step}/${payload.total} started`);
        break;
      case 'step_completed':
        log.info(
          `${prefix} [SSE] \u2713  Step ${payload.step}/${payload.total} completed \u2014 ${payload.message}`
        );
        break;
      case 'workflow_completed':
        log.info(`${prefix} [SSE] *** WORKFLOW COMPLETED \u2013 ${payload.total_steps} steps done ***`);
        break;
      case 'workflow_failed':
        log.error(`${prefix} [SSE] \u2717 WORKFLOW FAILED: ${payload.message}`);
        break;
      default:
        log.debug(`${prefix} [SSE] event=${ev.event}  payload=${JSON.stringify(payload)}`);
    }
  });
}

/**
 * STEP_MODE – workflow pauses after each step and waits for an explicit
 * resume call.  In interactive mode the user presses ENTER to continue;
 * with --auto-resume the client resumes automatically.
 */
async function runStepMode(server, autoResume = false, clientId = 1) {
  const prefix = `[client-${clientId}]`;
  log.info('='.repeat(60));
  log.info(`${prefix} Mode: STEP_MODE  (auto_resume=${autoResume})`);

  const data = await fetchJSON(`${server}/workflow/start`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ mode: 'STEP_MODE' }),
    timeout: 30_000,
  });

  const { workflow_execution_id } = data;
  log.info(`${prefix} Workflow started: workflow_execution_id=${workflow_execution_id}`);
  log.info(`${prefix} Subscribing to SSE stream...`);

  async function sendResume() {
    const body = await fetchJSON(
      `${server}/workflow/${workflow_execution_id}/resume`,
      { method: 'POST', timeout: 30_000 }
    );
    log.info(`${prefix} [CLIENT] Resume accepted: ${body.message}  (next step coming up...)`);
  }

  await consumeSSE(server, workflow_execution_id, async (ev) => {
    const payload = parseSSEJson(ev);
    switch (ev.event) {
      case 'connected':
        log.info(`${prefix} [SSE] Connected to stream for execution ${workflow_execution_id}`);
        break;
      case 'step_started':
        log.info(`${prefix} [SSE] \u25b6  Step ${payload.step}/${payload.total} started`);
        break;
      case 'step_completed':
        log.info(`${prefix} [SSE] \u2713  Step ${payload.step}/${payload.total} completed`);
        break;
      case 'awaiting_resume': {
        const { step, next_step, total } = payload;
        log.info(
          `${prefix} [SSE] \u23f8  PAUSED after step ${step}/${total} \u2014 waiting for resume`
        );
        log.info(`${prefix}        Resume URL: POST ${payload.resume_url}`);

        if (autoResume) {
          await sleep(500); // brief visual pause
          log.info(`${prefix} [CLIENT] Auto-resuming to step ${next_step}...`);
          await sendResume();
        } else {
          await promptEnter(
            `\n  >>> [${prefix}] Press ENTER to resume step ${next_step} (or Ctrl-C to abort)...\n`
          );
          await sendResume();
        }
        break;
      }
      case 'workflow_completed':
        log.info(`${prefix} [SSE] *** WORKFLOW COMPLETED \u2013 ${payload.total_steps} steps done ***`);
        break;
      case 'workflow_failed':
        log.error(`${prefix} [SSE] \u2717 WORKFLOW FAILED: ${payload.message}`);
        break;
      default:
        log.debug(`${prefix} [SSE] event=${ev.event}  payload=${JSON.stringify(payload)}`);
    }
  });
}

// ── CLI argument parsing ───────────────────────────────────────────────────────

function parseArgs() {
  const args = process.argv.slice(2);
  const opts = {
    mode: null,
    autoResume: false,
    server: DEFAULT_SERVER,
    clients: 1,
  };

  for (let i = 0; i < args.length; i++) {
    switch (args[i]) {
      case '--mode':
        opts.mode = args[++i];
        break;
      case '--auto-resume':
        opts.autoResume = true;
        break;
      case '--server':
        opts.server = args[++i];
        break;
      case '--clients':
        opts.clients = Math.max(1, parseInt(args[++i], 10) || 1);
        break;
      case '--help':
      case '-h':
        printHelp();
        process.exit(0);
        break;
      default:
        console.error(`Unknown option: ${args[i]}`);
        process.exit(1);
    }
  }

  if (!opts.mode) {
    console.error('Error: --mode is required (FULL_NO_SSE | FULL_WITH_SSE | STEP_MODE)');
    process.exit(1);
  }
  if (!['FULL_NO_SSE', 'FULL_WITH_SSE', 'STEP_MODE'].includes(opts.mode)) {
    console.error(
      `Error: invalid mode "${opts.mode}". Must be one of: FULL_NO_SSE, FULL_WITH_SSE, STEP_MODE`
    );
    process.exit(1);
  }

  return opts;
}

function printHelp() {
  console.log(`
SSE Workflow Client (Node.js)
==============================
Usage: node client.js --mode MODE [options]

Options:
  --mode MODE        Workflow mode: FULL_NO_SSE | FULL_WITH_SSE | STEP_MODE  (required)
  --auto-resume      (STEP_MODE only) Automatically send resume after each step
  --server URL       Server base URL (default: ${DEFAULT_SERVER})
  --clients N        Number of concurrent clients (default: 1). Each starts its own
                     independent workflow and receives a unique workflow_execution_id.
  --help, -h         Show this help

Examples:
  node client.js --mode FULL_NO_SSE
  node client.js --mode FULL_WITH_SSE
  node client.js --mode STEP_MODE --auto-resume
  node client.js --mode STEP_MODE                         # interactive (press ENTER)
  node client.js --mode FULL_WITH_SSE --clients 3
  node client.js --mode FULL_NO_SSE --clients 5
  node client.js --mode STEP_MODE --auto-resume --clients 2
  node client.js --mode FULL_WITH_SSE --server http://remote-host:8000
`);
}

// ── Entry point ────────────────────────────────────────────────────────────────

async function main() {
  const opts = parseArgs();
  const server = opts.server.replace(/\/$/, '');
  const numClients = opts.clients;

  // Verify server is reachable before starting
  try {
    const health = await fetchJSON(`${server}/health`, { timeout: 5_000 });
    log.info(`Server health: ${JSON.stringify(health)}`);
  } catch (err) {
    log.error(`Cannot reach server at ${server} – ${err.message}`);
    process.exit(1);
  }

  async function runClient(clientId) {
    switch (opts.mode) {
      case 'FULL_NO_SSE':  return runFullNoSSE(server, clientId);
      case 'FULL_WITH_SSE': return runFullWithSSE(server, clientId);
      case 'STEP_MODE':    return runStepMode(server, opts.autoResume, clientId);
    }
  }

  if (numClients === 1) {
    await runClient(1);
  } else {
    // Multi-client path – launch N concurrent workflow executions.
    // Each gets its own workflow_execution_id from the server.
    log.info(`Launching ${numClients} concurrent clients in mode=${opts.mode}`);

    // Promise.allSettled mirrors asyncio.gather(return_exceptions=True):
    // one failure does not abort the others.
    const results = await Promise.allSettled(
      Array.from({ length: numClients }, (_, i) => runClient(i + 1))
    );

    // Report any per-client failures
    for (let i = 0; i < results.length; i++) {
      if (results[i].status === 'rejected') {
        log.error(`client-${i + 1} raised an exception: ${results[i].reason}`);
      }
    }

    log.info(`All ${numClients} clients finished.`);
  }
}

main().catch(err => {
  log.error(`Fatal: ${err.message}`);
  process.exit(1);
});
