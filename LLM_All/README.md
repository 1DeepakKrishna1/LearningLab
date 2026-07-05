# AI Conversational Bot

A production-quality, full-stack conversational AI application built with **FastAPI** (Python) and **React** (TypeScript). Supports multiple LLM providers, per-conversation context management, configurable guardrails, and a rich admin dashboard.

---

## Features

| Area | Capability |
|------|-----------|
| **LLM Providers** | OpenAI (GPT-4o), Anthropic (Claude), Google (Gemini), Groq (Llama / Mixtral) |
| **Admin: API Keys** | Securely store/update keys in `.env` via the UI |
| **Admin: System Prompt** | Edit the system prompt and choose the active LLM + model |
| **Admin: Guardrails** | Keyword-block, output-filter, and topic-restriction rules stored in JSON |
| **Chat** | Streaming-ready conversation UI with follow-up suggestions |
| **Context Window** | Last *N* exchanges sent verbatim; older messages are LLM-summarised |
| **Logging** | Every message written to `logs/conversations.log` AND SQLite DB |
| **API Response** | Returns response, follow-up links, tokens consumed, and time taken |
| **Admin: Conversations** | List all conversations, view messages, analytics, AI summary & insights |

---

## Project Structure

```
LLM_All/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app entry point
│   │   ├── config.py            # Settings, .env helpers, JSON config loaders
│   │   ├── database.py          # SQLAlchemy engine + session
│   │   ├── models.py            # SQLAlchemy ORM models
│   │   ├── schemas.py           # Pydantic request/response schemas
│   │   ├── dependencies.py      # JWT auth dependencies
│   │   ├── routers/
│   │   │   ├── auth.py          # POST /api/auth/login
│   │   │   ├── chat.py          # POST /api/chat/{id}/message
│   │   │   └── admin.py         # /api/admin/* endpoints
│   │   └── services/
│   │       ├── llm_service.py       # Multi-provider LLM client
│   │       ├── guardrails_service.py # Input/output content filtering
│   │       ├── context_service.py    # Rolling context window + summarisation
│   │       ├── analytics_service.py  # Analytics, summary, insights generation
│   │       └── logging_service.py    # File logger
│   ├── data/
│   │   ├── system_config.json   # Active LLM, model, system prompt, context window
│   │   └── guardrails.json      # Guardrail rules
│   ├── logs/
│   │   └── conversations.log    # Structured JSON log of all messages
│   ├── conversations.db         # SQLite database (auto-created)
│   ├── .env                     # API keys (auto-created; gitignored)
│   ├── .env.example
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── api/client.ts        # Axios API client
│   │   ├── contexts/AuthContext.tsx
│   │   ├── pages/
│   │   │   ├── Login.tsx
│   │   │   ├── Chat.tsx
│   │   │   └── Admin.tsx
│   │   ├── components/
│   │   │   ├── chat/
│   │   │   │   ├── ChatWindow.tsx
│   │   │   │   └── MessageBubble.tsx
│   │   │   └── admin/
│   │   │       ├── ApiKeyManager.tsx
│   │   │       ├── SystemPromptManager.tsx
│   │   │       ├── GuardrailsManager.tsx
│   │   │       └── ConversationManager.tsx
│   │   └── types/index.ts
│   ├── package.json
│   └── vite.config.ts
└── README.md
```

---

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- At least one LLM API key

### 1 — Backend

```bash
cd backend

# Create virtual environment
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env and set SECRET_KEY, ADMIN_PASSWORD, and at least one LLM API key

# Start the server
uvicorn app.main:app --reload --port 8000
```

The API will be available at `http://localhost:8000`.  
Interactive docs: `http://localhost:8000/docs`

### 2 — Frontend

```bash
cd frontend

npm install
npm run dev
```

The app will be available at `http://localhost:5173`.

---

## Configuration

### Environment Variables (`.env`)

| Variable | Description | Default |
|----------|-------------|---------|
| `SECRET_KEY` | JWT signing secret — **change in production** | `change-me-in-production` |
| `ADMIN_USERNAME` | Admin login username | `admin` |
| `ADMIN_PASSWORD` | Admin login password | `admin123` |
| `OPENAI_API_KEY` | OpenAI API key | — |
| `ANTHROPIC_API_KEY` | Anthropic API key | — |
| `GOOGLE_API_KEY` | Google Generative AI key | — |
| `GROQ_API_KEY` | Groq API key (Llama / Mixtral) | — |

Keys can also be managed via the Admin UI → **API Keys** tab (written to `.env` automatically).

### System Config (`data/system_config.json`)

```json
{
  "active_llm": "openai",
  "models": {
    "openai": "gpt-4o",
    "anthropic": "claude-3-5-sonnet-20241022",
    "google": "gemini-1.5-pro",
    "groq": "llama-3.3-70b-versatile"
  },
  "system_prompt": "You are a helpful AI assistant...",
  "context_window": 5
}
```

`context_window` controls how many recent user/assistant pairs are sent verbatim. Messages older than the window are summarised by the LLM and injected as context.

---

## API Reference

### Authentication

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/auth/login` | Login (users auto-registered on first login). Returns JWT + conversation ID. |
| `GET` | `/api/auth/me` | Current user info |

**Login response:**
```json
{
  "access_token": "eyJ...",
  "token_type": "bearer",
  "conversation_id": "uuid",
  "username": "alice",
  "role": "user"
}
```

### Chat

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/chat/{conversation_id}/message` | Send a message and receive an AI response |
| `GET` | `/api/chat/{conversation_id}/history` | Retrieve full message history |

**Chat response:**
```json
{
  "conversation_id": "uuid",
  "message_id": "uuid",
  "query": "What is machine learning?",
  "response": "Machine learning is...",
  "follow_ups": [
    { "text": "Types of ML", "query": "What are the main types of machine learning?" }
  ],
  "tokens_consumed": { "input": 120, "output": 340, "total": 460 },
  "time_taken": 1.234,
  "guardrail_triggered": false,
  "timestamp": "2026-04-30T10:00:00"
}
```

### Admin (requires admin JWT)

| Method | Path | Description |
|--------|------|-------------|
| `GET/PUT` | `/api/admin/api-keys` | Read / update LLM API keys |
| `GET/PUT` | `/api/admin/system-config` | Read / update system prompt, active LLM, model |
| `GET/PUT` | `/api/admin/guardrails` | Read / update guardrail rules |
| `GET` | `/api/admin/conversations` | List all conversations |
| `GET` | `/api/admin/conversations/{id}` | Conversation detail with messages |
| `GET` | `/api/admin/conversations/{id}/analytics` | Token usage, response times, session stats |
| `GET` | `/api/admin/conversations/{id}/summary` | LLM-generated conversation summary |
| `GET` | `/api/admin/conversations/{id}/insights` | LLM-generated insights, sentiment, topics |

---

## Guardrails

Three rule types are supported:

| Type | When it runs | Effect |
|------|-------------|--------|
| `keyword_block` | Before LLM call (input check) | Blocks request if user input matches a keyword |
| `output_filter` | After LLM call (output check) | Replaces LLM response if it matches a keyword |
| `topic_restriction` | Before LLM call | Can be used for topic-level restrictions |

Rules are stored in `data/guardrails.json` and editable via the Admin UI without restart.

---

## Context Management

For each conversation turn:

1. All messages for the conversation are fetched from the database.
2. The **last N pairs** (default: 5) are sent to the LLM verbatim as message history.
3. If there are older messages, they are **summarised by the LLM** and injected as an assistant note at the start of the context window.
4. This ensures the model has full awareness of the conversation without exceeding token limits.

---

## Logging

All chat events are written to two sinks simultaneously:

- **File**: `backend/logs/conversations.log` — one JSON object per line, including username, conversation ID, role, content snippet, token counts, and response time.
- **Database**: `backend/conversations.db` — SQLite with `users`, `conversations`, and `messages` tables, enabling full replay and analytics.

---

## Production Deployment

### Backend

```bash
# Use a production ASGI server
pip install gunicorn
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

Key hardening steps:
- Set a strong `SECRET_KEY` in `.env`
- Replace SQLite with PostgreSQL for multi-process deployments
- Add HTTPS (nginx / Caddy in front of gunicorn)
- Restrict `allow_origins` in `main.py` to your frontend domain

### Frontend

```bash
cd frontend
npm run build
# Serve the dist/ folder with nginx or any static host
```

---

## Development Notes

- The backend auto-creates the SQLite database and default JSON config files on first start.
- New users are auto-registered on first login (no separate signup flow) — every login creates a fresh conversation.
- Admin credentials are set via `.env`; the admin account is created in the DB on first admin login.
- Follow-up suggestions are extracted from a structured JSON block that the LLM appends to its response.

---

## Tech Stack

**Backend:** FastAPI · SQLAlchemy · SQLite · Pydantic · python-jose · passlib · python-dotenv  
**LLM SDKs:** openai · anthropic · google-generativeai · groq  
**Frontend:** React 18 · TypeScript · Vite · Tailwind CSS · React Router · Axios · React Markdown · Lucide React
