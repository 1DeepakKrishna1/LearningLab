# RESTAPI AI Agent

An **LLM-powered agent that dynamically consumes any Swagger/OpenAPI specification and
invokes its REST APIs from natural language.** Tell it _"Create a customer named John"_
and it finds the right endpoint, fills in parameters, asks you for anything missing, and
(for write operations) pauses for your approval before executing the call.

- **Backend:** Python · FastAPI · OpenAI (function calling)
- **Frontend:** React + Vite (chat UI with live API-call inspection and approval gates)

---

## Architecture

```
┌──────────────┐   /api/chat        ┌─────────────────────────────────────────┐
│  React SPA   │ ─────────────────▶ │              FastAPI backend              │
│  (chat UI)   │ ◀───────────────── │                                           │
└──────────────┘  message/approval  │  Agent loop (OpenAI tool calling)         │
                                     │   ├─ search_endpoints   (NL → operations) │
                                     │   ├─ get_endpoint_details                 │
                                     │   ├─ invoke_api  ──► approval gate ──┐     │
                                     │   └─ ask_user (multi-turn clarify)   │     │
                                     │                                      ▼     │
                                     │  OpenAPI parser (2.0 / 3.x, $ref)  Executor│
                                     │  Endpoint search   Auth injection  (httpx)│
                                     └───────────────────────────┬───────────────┘
                                                                 ▼
                                                        Target REST API
```

The agent never hard-codes endpoints. Each ingested spec becomes a searchable operation
catalog; the LLM plans which operations to call and how to populate them. Mutating calls
(`POST/PUT/PATCH/DELETE`) are paused and surfaced to the user for explicit approval, then
the conversation resumes exactly where it left off.

### Key directories

| Path | Purpose |
|------|---------|
| `backend/app/openapi/` | Load + parse OpenAPI 2.0 / 3.x, resolve `$ref`, normalize to an operation catalog |
| `backend/app/services/agent.py` | The tool-calling agent: planning, clarification, approval pause/resume |
| `backend/app/services/executor.py` | Builds and sends REST requests (path/query/header/body), parses responses |
| `backend/app/services/search.py` | Natural-language endpoint search over the catalog |
| `backend/app/services/auth.py` | Injects API-key / Bearer / Basic credentials |
| `backend/app/routers/` | HTTP API: specs, chat, approvals, health |
| `frontend/src/` | React chat UI, spec management, auth panel, approval modal |

---

## Prerequisites

- Python 3.11+
- Node 18+
- An OpenAI API key

---

## Setup & run

### 1. Backend

```bash
cd backend
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate

pip install -r requirements.txt
cp .env.example .env        # then edit .env and set OPENAI_API_KEY
uvicorn app.main:app --reload --port 8000
```

API docs are served at <http://localhost:8000/docs>.

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
```

Open <http://localhost:5173>. The Vite dev server proxies `/api` to the backend.

---

## Using it

1. **Import a spec** in the sidebar — paste a URL (e.g.
   `https://petstore3.swagger.io/api/v3/openapi.json`), paste JSON/YAML, or upload a file.
2. **Set authentication** (optional) — API key, Bearer/JWT, or Basic. Credentials are sent
   per-request to the backend and injected into outbound calls; they are never persisted.
3. **Chat** — describe what you want in plain language. The agent will:
   - find the right endpoint(s),
   - ask follow-up questions for any missing required values,
   - chain multiple calls for multi-step goals,
   - pause for your approval before any write operation.

---

## Feature coverage (vs. the spec)

Implemented:

- **API discovery** — import via URL / file / paste, OpenAPI 2.0 & 3.x, multiple specs,
  URL refresh, `$ref` resolution, operation catalog, NL search.
- **NL → execution** — intent detection, endpoint selection, parameter extraction, missing
  parameter identification, multi-turn clarification, context-aware selection.
- **Dynamic invocation** — all HTTP methods; path/query/header/body population; JSON/text
  response parsing with structured records.
- **Auth** — API key, Bearer/JWT, Basic; credential injection.
- **Agentic planning** — multi-step task decomposition, chained calls, dependency
  resolution, reflection/retry on errors.
- **Human-in-the-loop** — approval gate for mutating/irreversible actions.
- **Session memory** — conversation + prior API responses retained per session.

Configurable / extension points (designed for, not exhaustively built):

- `APPROVAL_REQUIRED_METHODS` controls which methods require approval.
- `search.py` can be swapped for embeddings/vector search.
- `storage.py` is an in-memory store behind a thin interface — swap for Postgres/Redis for
  horizontal scaling and durable long-term memory.
- OAuth2/Azure AD/SAML, visual workflow builder, RAG, and contract testing from the spec
  are natural next layers on top of this core.

---

## Configuration

All backend config lives in `backend/.env` (see `.env.example`):

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENAI_API_KEY` | — | Required. OpenAI key. |
| `OPENAI_MODEL` | `gpt-4o` | Chat/reasoning model. |
| `OPENAI_BASE_URL` | — | Optional override (Azure OpenAI / proxy). |
| `AGENT_MAX_STEPS` | `12` | Max tool-calling iterations per user turn. |
| `APPROVAL_REQUIRED_METHODS` | `POST,PUT,PATCH,DELETE` | Methods gated by human approval. |
| `CORS_ORIGINS` | `http://localhost:5173,...` | Allowed frontend origins. |
| `HTTP_TIMEOUT` | `30` | Outbound REST timeout (seconds). |

---

## Security notes

- Credentials are held only in server-side session memory for the life of the process and
  injected per outbound request — never logged or written to disk.
- Human approval is enforced server-side: the agent **cannot** execute a gated method
  without an explicit approval call, even if the model tries.
- For production: put this behind auth, use HTTPS, back sessions/specs with a real store,
  and add a secret vault for credentials.
```
