# Deployment Guide — ClawFlow

This covers local development, Docker, and production hardening.

---

## 1. Prerequisites

- Python 3.11+
- Node.js 20+ / npm 10+
- (Optional) An LLM API key for agent execution & the AI builder
  (`ANTHROPIC_API_KEY` recommended — Claude is the default provider).
- The `agents_tools_library` checkout next to `platform/` (the default
  `CLAWFLOW_TOOL_LIBRARY_PATH` points at `../../agents_tools_library/library`).

---

## 2. Configuration

All backend config is environment-driven (prefix `CLAWFLOW_`). Copy
`backend/.env.example` → `backend/.env`. Important keys:

| Key | Default | Notes |
|-----|---------|-------|
| `CLAWFLOW_JWT_SECRET` | dev value | **Set a strong secret in production.** |
| `CLAWFLOW_BOOTSTRAP_ADMIN_EMAIL/PASSWORD` | admin@clawflow.local / admin123 | First-run admin. **Change it.** |
| `CLAWFLOW_DATA_DIR` | `./data` | JSON storage location. |
| `CLAWFLOW_TOOL_LIBRARY_PATH` | `../../agents_tools_library/library` | Tool source. |
| `CLAWFLOW_TOOL_LIBRARY_PYTHONPATH` | `../../agents_tools_library` | Makes `library.tools.*` importable. |
| `CLAWFLOW_DEFAULT_LLM_PROVIDER` / `_MODEL` | anthropic / claude-sonnet-4-6 | Agent + AI builder default. One of `anthropic` / `openai` / `google` / `ollama` / `groq`. |
| `CLAWFLOW_MESSAGING_PROVIDER` | console | `meta` or `twilio` for WhatsApp. |
| `ANTHROPIC_API_KEY` / `OPENAI_API_KEY` / `GEMINI_API_KEY` / `GROQ_API_KEY` | — | Provide the key matching your chosen provider — required for live agent/AI features. |
| `GROQ_MODEL` | llama-3.3-70b-versatile | Default Groq model when `CLAWFLOW_DEFAULT_LLM_MODEL` is unset. |

> **Using Groq:** set `CLAWFLOW_DEFAULT_LLM_PROVIDER=groq`,
> `CLAWFLOW_DEFAULT_LLM_MODEL=llama-3.3-70b-versatile` (or any Groq model), and
> `GROQ_API_KEY=gsk_...`. Per-agent overrides (`provider`/`model` on an agent) also
> work, so different agents can target different providers.

---

## 3. Local development

**Backend**
```powershell
cd platform/backend
python -m venv .venv ; .venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

**Frontend**
```powershell
cd platform/frontend
npm install
npm run dev
```

The Vite dev server proxies `/api` and `/ws` to `:8000`, so no CORS config is needed
in dev. For a different backend host set `VITE_API_BASE` in `frontend/.env`.

---

## 4. Production build

**Frontend** → static assets:
```powershell
cd platform/frontend
npm run build        # outputs dist/
```
Serve `dist/` from any static host / CDN, or behind the same reverse proxy as the API.

**Backend** → run under a production ASGI server:
```bash
cd platform/backend
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1
```

> **Note on workers:** the JSON storage backend is single-process (an in-process
> async lock guards writes). Run **one** Uvicorn worker. To scale horizontally,
> implement a `Repository` backed by a shared database (the seam is already in
> `app/storage/repository.py`) and then increase workers.

---

## 5. Docker (reference)

`backend/Dockerfile`:
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY platform/backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY agents_tools_library /agents_tools_library
COPY platform/backend /app
ENV CLAWFLOW_TOOL_LIBRARY_PATH=/agents_tools_library/library \
    CLAWFLOW_TOOL_LIBRARY_PYTHONPATH=/agents_tools_library \
    CLAWFLOW_DATA_DIR=/data
VOLUME ["/data"]
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

`frontend/Dockerfile`:
```dockerfile
FROM node:20-alpine AS build
WORKDIR /app
COPY platform/frontend/package*.json ./
RUN npm ci
COPY platform/frontend .
RUN npm run build
FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
# proxy /api and /ws to the backend service in nginx.conf
```

`docker-compose.yml` (sketch):
```yaml
services:
  backend:
    build: { context: ., dockerfile: platform/backend/Dockerfile }
    environment: [ "CLAWFLOW_JWT_SECRET=${JWT_SECRET}", "ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}" ]
    volumes: [ "clawflow-data:/data" ]
    ports: [ "8000:8000" ]
  frontend:
    build: { context: ., dockerfile: platform/frontend/Dockerfile }
    ports: [ "5173:80" ]
    depends_on: [ backend ]
volumes: { clawflow-data: {} }
```

---

## 6. WhatsApp setup

1. Set `CLAWFLOW_MESSAGING_PROVIDER=meta` (or `twilio`) and the matching credentials
   (`META_WHATSAPP_TOKEN`, `META_PHONE_NUMBER_ID`, or `TWILIO_*`).
2. Point the provider's webhook at `POST /api/whatsapp/webhook` (Meta verification
   uses `GET /api/whatsapp/webhook`).
3. Users can then text commands ("create a workflow that…", "run <name>", "status")
   and reply `APPROVE <id>` / `REJECT <id>` to action approvals.

---

## 7. Production hardening checklist

- [ ] Strong `CLAWFLOW_JWT_SECRET`; rotate admin password.
- [ ] Run behind HTTPS (reverse proxy / load balancer).
- [ ] Restrict `CLAWFLOW_CORS_ORIGINS` to your frontend origin.
- [ ] Back up `CLAWFLOW_DATA_DIR` (or migrate to a DB `Repository`).
- [ ] Set per-agent `limits` (max_iterations, timeout, tool_allow_list, sandboxed)
      and assign least-privilege roles.
- [ ] Single Uvicorn worker for JSON storage; scale via a DB backend.
- [ ] Monitor `/health` and the audit log.
```
