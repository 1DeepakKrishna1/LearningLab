# 🦅 ClawFlow — Agentic Workflow Automation Platform

A production-grade, visual, agent-driven workflow automation platform built on the
**OpenClaw** agent runtime and the existing **agents-tools-library** (~144 tools
auto-discovered). Think n8n / LangFlow / Dify / CrewAI Studio — but powered by
OpenClaw agents and a dynamic tool registry.

> Full architecture, schemas and diagrams: [ARCHITECTURE.md](./ARCHITECTURE.md).

---

## What it does

- **Visual workflow builder** (React Flow) — drag-drop triggers, agents, logic,
  tool and action nodes onto a canvas, connect them, configure, run.
- **Dynamic tool registry** — scans `agents_tools_library/library/tools/**`, parses
  each `README.md`, builds JSON schemas, and exposes every tool as a workflow node
  **and** an OpenClaw agent tool — *no code changes to add a tool*.
- **Workflow engine** — async DAG executor with conditional branching, parallelism,
  retry/timeout policies, checkpointing, compensation, and human-in-the-loop
  approvals (suspend/resume).
- **OpenClaw agent layer** — Supervisor / Planner / Executor / Researcher / Reviewer
  / Custom agents with tool-calling, memory, and per-agent security limits.
- **AI Workflow Builder** — natural-language → workflow graph (LLM, with a
  deterministic fallback).
- **AI Chatbot** + **WhatsApp** integration (Meta / Twilio / pluggable) for creating,
  running, querying and approving workflows conversationally.
- **Security** — JWT auth + RBAC (admin / designer / operator / viewer), per-agent
  tool allow-lists, execution limits, and a full audit log.
- **Monitoring** — live dashboard, execution timeline, WebSocket event stream.

---

## Tech stack

| Layer        | Tech |
|--------------|------|
| Frontend     | React 19, TypeScript, Vite, Tailwind, Material UI, React Flow, Zustand, Axios |
| Backend      | FastAPI, Pydantic v2, Uvicorn, asyncio |
| Agent runtime| OpenClaw (LangChain tool-calling + MCP). Providers: Anthropic (default) / OpenAI / Google / Ollama / **Groq** — set `CLAWFLOW_DEFAULT_LLM_PROVIDER` + matching key in `.env`. |
| Storage      | JSON files behind a `Repository` abstraction (DB-swappable) |

---

## Repository layout

```
platform/
├── ARCHITECTURE.md          # design, diagrams, schemas, roadmap
├── DEPLOYMENT.md            # how to run / deploy
├── README.md                # this file
├── samples/                 # sample workflow JSON
├── backend/                 # FastAPI app  (see backend/app/*)
│   ├── app/{domain,storage,registry,agents,engine,ai_builder,messaging,security,services,api}
│   ├── scripts/seed_samples.py
│   └── tests/{unit,integration}
└── frontend/                # React 19 app (see frontend/src/*)
    └── src/{api,store,components,pages}
```

---

## Quick start

### 1. Backend

```powershell
cd platform/backend
python -m venv .venv ; .venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env        # optional; add ANTHROPIC_API_KEY for agents/AI builder
uvicorn app.main:app --reload
```

- API: <http://localhost:8000>  ·  Swagger: <http://localhost:8000/docs>  ·  OpenAPI: `/openapi.json`
- First run auto-discovers 144 tools and seeds an admin user
  (`admin@clawflow.local` / `admin123` — change via `.env`).

Seed the sample workflows (optional):

```powershell
python -m scripts.seed_samples
```

### 2. Frontend

```powershell
cd platform/frontend
npm install
npm run dev      # http://localhost:5173  (proxies /api → :8000)
```

Log in with the bootstrap admin, open **Workflows → New Workflow** (or the **AI
Builder**), drag nodes, **Save**, then **Run**, and watch **Executions** /
**Dashboard** update live.

---

## The tool registry (no-code tool onboarding)

Drop a new tool into `agents_tools_library/library/tools/<category>/<name>/` with a
`tool.py` (a `BaseTool` subclass) and a `README.md`, then hit **Tool Library →
Rescan Library** (or `POST /api/tools/refresh`). It immediately becomes:

1. a manifest in `tool_registry.json` (parsed params, schema, examples),
2. a draggable **tool node** in the builder palette,
3. an available **agent tool** in the OpenClaw runtime.

Validated end-to-end against the real library: **144 tools across 9 categories**.

---

## Key APIs

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/api/auth/login` | JWT login |
| GET  | `/api/tools` · `/api/tools/{id}` | list / inspect tools |
| POST | `/api/tools/execute` | run a tool directly |
| POST | `/api/tools/refresh` | rescan the library |
| GET/POST | `/api/workflows` | list / create workflows |
| POST | `/api/workflows/{id}/run` | execute a workflow |
| POST | `/api/workflows/generate` | AI builder (NL → workflow) |
| GET  | `/api/executions` · `/api/executions/{id}` | monitor runs |
| GET/POST | `/api/agents` (+ `/api/agent/list`, `/api/agent/create`) | manage agents |
| POST | `/api/approvals/respond` (+ `/api/approval/respond`) | HITL decisions |
| GET  | `/api/audit` · `/api/monitoring/dashboard` | audit & metrics |
| POST | `/api/chat` | AI chatbot |
| POST | `/api/whatsapp/webhook` | inbound WhatsApp |
| WS   | `/ws/events` | live execution events |

The spec's exact endpoints (`/workflow/create`, `/workflow/run`,
`/workflow/status/{id}`, `/agent/create`, `/agent/list`, `/tools`,
`/tools/execute`, `/approval/respond`) are all provided as aliases.

---

## Tests

```powershell
cd platform/backend
python -m pytest tests/ -q      # 32 unit + integration tests
```

Covers: README parser, schema builder, JSON storage, RBAC/JWT, DAG validation, the
engine (conditional branch + skip + approval suspend/resume), tool discovery against
the real library, and the full HTTP API surface.

---

## Design principles

Clean Architecture · Dependency Injection (single `Container`) · async-first ·
configuration-driven · storage-agnostic (`Repository` seam) · type-safe (Pydantic v2)
· comprehensive logging & audit · graceful degradation (works without an LLM key —
agent/AI features return structured errors instead of crashing).
