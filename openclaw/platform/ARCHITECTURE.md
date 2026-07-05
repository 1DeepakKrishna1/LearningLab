# ClawFlow — Agentic Workflow Automation Platform

> Production-grade, visual, agent-driven workflow automation built on the **OpenClaw**
> agent runtime and the existing **agents-tools-library** (~180 auto-discovered tools).
>
> Comparable to n8n / LangFlow / Dify / CrewAI Studio / Copilot Studio, but powered by
> OpenClaw agents and a dynamically-discovered tool registry.

---

## 1. High-level architecture

```
                              ┌───────────────────────────────────────────────┐
                              │                  FRONTEND (React 19)          │
                              │  Vite · TS · Tailwind · MUI · React Flow ·    │
                              │  Zustand · Axios                              │
                              │                                               │
                              │  Dashboard │ Workflow Builder │ Executions │  │
                              │  Agents │ Tool Library │ Approvals │ Audit │  │
                              │  Settings │ Chatbot                           │
                              └───────────────┬───────────────────────────────┘
                                              │ REST + WebSocket (JSON, JWT)
                              ┌───────────────▼─────────────────────────────────┐
                              │                 BACKEND (FastAPI, async)        │
                              │                                                 │
                              │  ┌─────────── API layer (routers) ───────────┐  │
                              │  │ auth · workflows · executions · agents ·  │  │
                              │  │ tools · approvals · audit · monitoring ·  │  │
                              │  │ chatbot · webhooks · whatsapp · settings  │  │
                              │  └────────────────────┬──────────────────────┘  │
                              │  ┌────────────────────▼──────────────────────┐  │
                              │  │            Service layer (use-cases)      │  │
                              │  └──┬─────────┬─────────┬──────────┬───────┬─┘  │
                              │     │         │         │          │       │    │
                              │ ┌───▼───┐ ┌───▼────┐ ┌──▼─────┐ ┌──▼────┐ ┌─▼──┐ │
                              │ │Workflow│ │ Agent  │ │ Tool   │ │  AI   │ │HITL│ │
                              │ │Engine  │ │Runtime │ │Registry│ │Builder│ │    │ │
                              │ │(DAG)   │ │Manager │ │        │ │       │ │    │ │
                              │ └───┬────┘ └───┬────┘ └──┬─────┘ └───────┘ └────┘ │
                              │     │          │         │                        │
                              │ ┌───▼──────────▼─────────▼──────────────────────┐ │
                              │ │  OpenClaw integration layer (LangChain + MCP)  │ │
                              │ │  AgentExecutor ◄─ MCP stdio ─► tool subprocess │ │
                              │ └────────────────────────────────────────────────┘ │
                              │  ┌──────────────── Cross-cutting ────────────────┐ │
                              │  │ Security (JWT/RBAC) · Audit · Logging ·        │ │
                              │  │ Config · Messaging (WhatsApp/Twilio) · Sched.  │ │
                              │  └────────────────────────────────────────────────┘ │
                              │  ┌──────────── Storage abstraction ──────────────┐  │
                              │  │  Repository[T]  ◄── JsonRepository (default)  │  │
                              │  │                 ◄── (future) SqlRepository    │  │
                              │  └───────────────────────────────────────────────┘  │
                              └───────────────┬─────────────────────────────────────┘
                                              │ scans / imports
                              ┌───────────────▼─────────────────────────────────┐
                              │     agents_tools_library/library/tools/**       │
                              │     (tool.py + README.md, ~180 tools)           │
                              └─────────────────────────────────────────────────┘
```

### Design principles
- **Clean Architecture**: `domain` (entities/schemas) ← `services` (use-cases) ← `api` (delivery).
  Inner layers never import outer layers.
- **Dependency Injection**: a single `Container` wires repositories, registry, runtime, engine.
  Routers receive collaborators through FastAPI `Depends`, never construct them.
- **Async-first**: all I/O is `async`; blocking tool code runs in a thread executor.
- **Configuration-driven**: every path, secret, policy and feature flag comes from `Settings`.
- **Storage-agnostic**: business code depends on the `Repository` protocol, not on JSON. A SQL
  implementation can be dropped in without touching services.
- **Type-safe**: Pydantic v2 models everywhere; mypy-clean.

---

## 2. Backend folder structure

```
platform/backend/
├── pyproject.toml
├── requirements.txt
├── .env.example
├── app/
│   ├── main.py                 # FastAPI app factory + lifespan
│   ├── config.py               # Settings (pydantic-settings)
│   ├── container.py            # DI container (composition root)
│   ├── logging_setup.py        # structured logging
│   ├── domain/                 # entities + schemas (no I/O)
│   │   ├── enums.py
│   │   ├── ids.py
│   │   ├── tool.py
│   │   ├── agent.py
│   │   ├── workflow.py         # nodes, edges, graph, JSON schema
│   │   ├── execution.py        # execution + node-run states
│   │   ├── approval.py
│   │   ├── user.py
│   │   ├── audit.py
│   │   └── settings_model.py
│   ├── storage/
│   │   ├── repository.py       # Repository[T] protocol + Entity base
│   │   ├── json_repository.py  # async JSON-file implementation (atomic writes, locks)
│   │   └── unit_of_work.py     # repository registry / factory
│   ├── registry/               # TOOL REGISTRY FRAMEWORK
│   │   ├── readme_parser.py    # parse README.md → params/returns/examples
│   │   ├── discovery.py        # scan library/tools/** → ToolManifest
│   │   ├── schema_builder.py   # ToolManifest → JSON Schema
│   │   ├── tool_registry.py    # in-memory registry, refresh, lookup
│   │   └── openclaw_tool.py    # wrap a discovered tool as a LangChain/OpenClaw tool
│   ├── agents/                 # OPENCLAW AGENT LAYER
│   │   ├── runtime.py          # AgentRuntimeManager (build + run agents)
│   │   ├── openclaw_agent.py   # OpenClaw agent backed by LangChain + MCP tools
│   │   ├── prompts.py          # role system prompts (supervisor/planner/...)
│   │   └── memory.py           # conversation / scratchpad memory
│   ├── engine/                 # WORKFLOW ENGINE
│   │   ├── context.py          # ExecutionContext (shared state, IO between nodes)
│   │   ├── graph.py            # topological sort, cycle detection, DAG helpers
│   │   ├── policies.py         # retry + timeout policies
│   │   ├── checkpoint.py       # checkpoint persistence (resume after pause/approval)
│   │   ├── executor.py         # async DAG executor (the heart)
│   │   └── nodes/              # one handler per node category
│   │       ├── base.py         # NodeHandler protocol + registry
│   │       ├── triggers.py     # manual/http/cron/webhook/email/whatsapp/file/sheet
│   │       ├── agents.py       # openclaw/supervisor/planner/research/executor/reviewer
│   │       ├── logic.py        # if/switch/parallel/merge/loop/wait/approval
│   │       ├── tools.py        # dynamic tool node
│   │       └── actions.py      # send email/whatsapp/api call/file write/report
│   ├── ai_builder/
│   │   └── generator.py        # NL prompt → workflow JSON (intent→tools→graph→json)
│   ├── messaging/              # WHATSAPP INTEGRATION FRAMEWORK
│   │   ├── base.py             # MessagingProvider ABC
│   │   ├── factory.py          # provider resolution from settings
│   │   └── providers/          # console, meta(whatsapp), twilio, (telegram/teams/slack stubs)
│   ├── security/
│   │   ├── jwt_handler.py      # encode/decode JWT
│   │   ├── passwords.py        # hashing
│   │   ├── rbac.py             # Role/Permission matrix + require(...) dependency
│   │   └── deps.py             # current_user / role guards
│   ├── services/               # USE-CASES (orchestrate domain + infra)
│   │   ├── auth_service.py
│   │   ├── workflow_service.py
│   │   ├── execution_service.py
│   │   ├── agent_service.py
│   │   ├── tool_service.py
│   │   ├── approval_service.py
│   │   ├── audit_service.py
│   │   ├── monitoring_service.py
│   │   └── chatbot_service.py
│   └── api/
│       ├── deps.py             # shared Depends() providers from the container
│       ├── errors.py           # exception handlers → RFC7807 problem+json
│       ├── ws.py               # WebSocket hub for live execution events
│       └── routes/             # auth, workflows, executions, agents, tools,
│                               # approvals, audit, monitoring, chatbot,
│                               # webhooks, whatsapp, settings
├── data/                       # JSON storage (gitignored content, seeded on first run)
│   ├── agents.json  workflows.json  executions.json  tool_registry.json
│   ├── users.json   audit_logs.json approvals.json   settings.json
└── tests/
    ├── unit/                   # registry parser, engine, rbac, storage
    └── integration/            # API + end-to-end workflow run
```

---

## 3. Core schemas

### 3.1 Tool (registry) — `tool_registry.json`
```jsonc
{
  "id": "outlook.send_email",            // category.tool_name (stable)
  "name": "send_email",
  "display_name": "Send Email",
  "category": "outlook",
  "description": "Send an email via Microsoft Outlook ...",
  "impl_path": "library.tools.outlook.send_email.tool",
  "class_name": "SendEmailTool",
  "parameters": [                          // parsed from README "Input Parameters"
    {"name": "to",      "type": "string|array", "required": true,  "default": null,
     "description": "Recipient address(es)."},
    {"name": "subject", "type": "string",       "required": true,  "default": null, "...": ""}
  ],
  "returns": [{"field": "status", "type": "string", "description": "success or error"}],
  "input_schema": { "type": "object", "properties": { "...": {} }, "required": ["to","subject"] },
  "examples": [ { "...": "from README" } ],
  "tags": ["email","outlook","communication"],
  "icon": "mail", "color": "#0078D4",
  "discovered_at": "2026-05-29T12:00:00Z",
  "source": "readme|introspection"
}
```

### 3.2 Agent — `agents.json`
```jsonc
{
  "agent_id": "uuid",
  "name": "Invoice Reviewer",
  "description": "Reviews extracted invoice data for anomalies.",
  "role": "reviewer",                      // supervisor|planner|executor|researcher|reviewer|custom
  "type": "openclaw",
  "tools": ["pdf_tools.pdf_extract_text", "excel_tools.excel_write"],
  "model": "claude-sonnet-4-6",
  "provider": "anthropic",
  "temperature": 0.0,
  "system_prompt": "optional override",
  "capabilities": ["tool_calling","memory","planning","reflection","delegation"],
  "limits": {"max_iterations": 12, "timeout_seconds": 300, "tool_allow_list": ["..."]},
  "created_at": "...", "updated_at": "..."
}
```

### 3.3 Workflow — `workflows.json`  (React-Flow-compatible)
```jsonc
{
  "id": "uuid", "name": "Invoice Intake", "version": 3, "status": "draft|published",
  "nodes": [
    {"id": "n1", "type": "trigger.email", "position": {"x":0,"y":0},
     "data": {"label": "New Invoice Email", "config": {"folder": "Inbox", "filter": "invoice"}}},
    {"id": "n2", "type": "agent.executor", "position": {"x":250,"y":0},
     "data": {"label": "Extract", "agent_id": "uuid", "config": {}}},
    {"id": "n3", "type": "logic.approval", "position": {"x":500,"y":0},
     "data": {"label": "Approve > $10k", "config": {"channel": "ui", "approvers": ["..."]}}},
    {"id": "n4", "type": "tool.excel_tools.excel_write", "position": {"x":750,"y":0},
     "data": {"label": "Store", "config": {"file_path": "invoices.xlsx"}}}
  ],
  "edges": [
    {"id":"e1","source":"n1","target":"n2"},
    {"id":"e2","source":"n2","target":"n3"},
    {"id":"e3","source":"n3","target":"n4","sourceHandle":"approved"}
  ],
  "variables": {}, "created_by": "uuid", "created_at": "...", "updated_at": "..."
}
```

### 3.4 Execution — `executions.json`
```jsonc
{
  "id": "uuid", "workflow_id": "uuid", "workflow_version": 3,
  "status": "pending|running|paused|waiting_approval|completed|failed|cancelled",
  "trigger": {"type": "manual", "payload": {}},
  "context": { "variables": {}, "node_outputs": {"n1": {...}} },
  "node_runs": [
    {"node_id":"n1","status":"completed","attempts":1,"started_at":"...","finished_at":"...",
     "output":{...},"error":null}
  ],
  "checkpoint": { "completed_nodes": ["n1","n2"], "pending": ["n3"] },
  "started_at":"...", "finished_at":null, "created_by":"uuid"
}
```

### 3.5 Approval / Audit / User
```jsonc
// approvals.json
{"id":"uuid","execution_id":"uuid","node_id":"n3","status":"pending|approved|rejected|changes_requested|escalated",
 "channel":"ui|email|whatsapp","approvers":["uuid"],"decided_by":null,"comment":null,"created_at":"...","payload":{}}

// audit_logs.json
{"id":"uuid","timestamp":"...","actor":"user|agent|system","actor_id":"...","workflow":"...",
 "agent":"...","action":"tool_call|workflow_run|login|approval_decision|...","result":"success|error","detail":{}}

// users.json
{"id":"uuid","email":"...","name":"...","password_hash":"...","role":"admin|designer|operator|viewer",
 "active":true,"created_at":"..."}
```

---

## 4. Node taxonomy (engine)

| Group   | `type` prefix        | Nodes |
|---------|----------------------|-------|
| Trigger | `trigger.*`          | manual, http, cron, webhook, email, whatsapp, file_upload, google_sheet_row |
| Agent   | `agent.*`            | openclaw, supervisor, planner, research, executor, reviewer |
| Logic   | `logic.*`            | if_else, switch, parallel, merge, loop, wait, approval |
| Tool    | `tool.<cat>.<name>`  | dynamically generated from the registry |
| Action  | `action.*`           | send_email, send_whatsapp, api_call, file_write, generate_report |

Each handler implements `NodeHandler.execute(node, ctx) -> NodeResult`. New tool nodes need **no
code** — the generic `tool.*` handler resolves the registry entry and invokes it.

---

## 5. Execution model

1. **Validate** graph (DAG, no cycles, single-trigger reachability) → topological order.
2. **Schedule** ready nodes (in-degree 0 among remaining); run independent branches concurrently
   (`asyncio.gather`) up to a concurrency cap.
3. Each node runs under its **retry** (exponential backoff) and **timeout** policy.
4. After each node, **checkpoint** is persisted → crash/pause-resumable.
5. **Approval / Wait** nodes transition the execution to `waiting_approval`/`paused` and suspend;
   an external event (UI/WhatsApp/email/timer) resumes from the checkpoint.
6. On failure: run **compensation** handlers of completed nodes (best-effort), mark `failed`.
7. Live `node.*` events are pushed over WebSocket and written to the audit log.

---

## 6. OpenClaw integration

- An **OpenClaw agent** = a LangChain tool-calling agent (`get_llm()` from the existing library)
  whose tools are the registry tools, exposed through the library's **MCP stdio server**
  (`library/mcp/server.py`) or via direct in-process adapters.
- `AgentRuntimeManager` builds an agent from its `agents.json` record: resolves the tool
  allow-list against the registry, applies the role system prompt, wires memory, and enforces
  `limits` (max iterations, timeout, sandboxing).
- Multi-agent collaboration (Supervisor → Planner/Executor/Reviewer delegation) is modelled as
  agent nodes wired in the graph **and** as in-agent delegation tools.

---

## 7. Security

- **JWT** bearer auth (`/auth/login` → access token); passwords hashed (pbkdf2/bcrypt).
- **RBAC**: `admin > designer > operator > viewer`. Permission matrix maps each route to a
  minimum role. Agent security: per-agent **tool allow-list**, **execution limits**, **timeouts**,
  and a **sandbox flag** that restricts filesystem/network tool categories.
- Every privileged action is written to `audit_logs.json`.

---

## 8. Implementation roadmap

| Phase | Deliverable | Status |
|-------|-------------|--------|
| 0 | Architecture, schemas, folder structure (this doc) | ✅ |
| 1 | Backend foundation: config, logging, DI, app factory | ▶ |
| 2 | Domain schemas (Pydantic) | |
| 3 | Storage abstraction + JSON repositories | |
| 4 | **Tool Registry Framework** (discovery, README parse, schema, OpenClaw wrapper) + tests | |
| 5 | Agent Runtime Manager + OpenClaw agent layer | |
| 6 | Workflow Engine (DAG, policies, checkpoint, HITL) + node handlers | |
| 7 | Security (JWT + RBAC) + Audit | |
| 8 | Messaging/WhatsApp abstraction + AI Workflow Builder | |
| 9 | API routers + OpenAPI + monitoring/WebSocket | |
| 10 | React frontend (9 pages + React Flow designer) | |
| 11 | Tests (unit + integration), README, deployment guide, sample workflows | |

Items run roughly in order; the **vertical slice** target is: discover tools → build an agent →
design a workflow → run it end-to-end with approval → observe it in the dashboard.
```
