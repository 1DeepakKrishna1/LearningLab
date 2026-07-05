# Campaign Management Platform

A self-hosted **Omnichannel Campaign Management Platform** supporting Email, SMS, and
Push campaigns — built with FastAPI + SQLite (backend) and React + TypeScript +
Vite + MUI (frontend). Everything runs locally.

> **Status:** Production-quality foundation covering all 18 spec modules with working
> CRUD + UI end-to-end. Providers default to safe **console/sandbox** adapters that
> log instead of sending and emit synthetic events so analytics work out of the box.
> Deeper areas (real provider SDK error mapping, advanced drip timing, scheduled-report
> cron, 1M-contact scale tuning) are clearly marked with `TODO` and documented in
> [`docs/DESIGN.md` §19 Risks](docs/DESIGN.md).

---

## Architecture at a glance

```
Campaign/
├── backend/     FastAPI · SQLAlchemy · Alembic · Pydantic · APScheduler-style asyncio loop
├── frontend/    React · TypeScript · Vite · MUI · TanStack Query · Zustand · Recharts
├── data/        JSON config / provider / metadata / sample-data files
└── docs/        Full 19-section design document + diagrams
```

See [docs/DESIGN.md](docs/DESIGN.md) for the complete design (vision → roadmap → risks),
ER/state/sequence Mermaid diagrams, RBAC matrix, and API/UI specs.

---

## Quickstart

### Prerequisites
- Python 3.11+ (spec targets 3.12+; code is 3.11-compatible)
- Node.js 18+

### 1. Backend

```bash
cd backend
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
# source .venv/bin/activate

pip install -r requirements.txt
copy .env.example .env          # (cp on macOS/Linux)

alembic upgrade head            # create the SQLite schema
python -m app.seed              # load roles, demo users, providers, sample data
uvicorn app.main:app --reload   # http://localhost:8000  (Swagger at /docs)
```

### 2. Frontend

```bash
cd frontend
npm install
npm run dev                     # http://localhost:5173 (proxies /api -> :8000)
```

### 3. Log in

| Role     | Email             | Password       |
|----------|-------------------|----------------|
| Admin    | `admin@local`     | `Admin@123`    |
| Marketer | `marketer@local`  | `Marketer@123` |
| Viewer   | `viewer@local`    | `Viewer@123`   |

### 4. End-to-end smoke test
1. **Templates** → create or use the seeded *Welcome Email*.
2. **Segments** → use *US Pro Users* (or build one; preview shows the live count).
3. **Campaigns → New Campaign** → pick channel + template + segment → create.
4. Open the campaign → **Submit for Approval → Approve → Send Now**.
5. **Analytics** / campaign details show sent/delivered/opened/clicked (synthetic console events).

---

## Testing

```bash
cd backend
pytest                 # 16 unit + API/integration tests
```

```bash
cd frontend
npm run build          # tsc typecheck + Vite production build
```

---

## Provider modes

All providers ship in **console** mode (sandbox): messages are logged and synthetic
`delivered/opened/clicked` events are produced. To send for real:

1. Fill credentials in `data/providers/<type>.json` (e.g. `smtp.json`, `sendgrid.json`).
2. Switch the provider to `live`:
   `PATCH /api/v1/providers/{id}  { "mode": "live" }`.
3. (Optional) install the relevant SDK from the commented block in `requirements.txt`.

SMTP, SendGrid, and Twilio have working live implementations; FCM/OneSignal live mode
is stubbed (`TODO`) and falls back to sandbox.

---

## Key endpoints

- Interactive API docs: **http://localhost:8000/docs** (OpenAPI auto-generated)
- Health check: `GET /health`
- Auth: `POST /api/v1/auth/login` (OAuth2 password form), `/auth/refresh`, `/auth/me`

Full API reference: [docs/DESIGN.md §9](docs/DESIGN.md).
