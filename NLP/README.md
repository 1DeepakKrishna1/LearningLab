# NLP Data Intelligence Platform

A production-grade, full-stack application that lets you upload datasets (CSV/XLS/XLSX), explore them with **natural language queries**, build interactive dashboards, and generate exportable reports — all powered by a hybrid NLP engine (rule-based + optional LLM fallback).

---

## Architecture

```
NLP Data Intelligence Platform
├── backend/          FastAPI · Python 3.11 · SQLAlchemy (async) · aiosqlite
└── frontend/         React 18 · TypeScript · Material UI · Recharts
```

### Backend layer overview

| Layer | Module | Responsibility |
|-------|--------|----------------|
| API | `app/api/v1/` | REST endpoints — datasets, query, analytics, dashboards, reports |
| Services | `app/services/` | Business logic — ingestion, metadata, NLP engine, SQL builder, analytics, dashboards, reports |
| Core | `app/core/` | Security (SQL injection guard), TTL cache, structured logging |
| Models | `app/models/` | SQLAlchemy ORM — Dataset, DatasetColumn, Dashboard, Widget, Report, ReportSection |
| Schemas | `app/schemas/` | Pydantic v2 request/response models |

### NLP Query Pipeline

```
User query
    │
    ▼
Intent Detection  ──────────────────────────────────────────────────────────┐
  (regex, 15+ patterns)                                                      │
    │                                                                        │
    ▼                                                                        │
Entity Extraction                                                            │
  (column fuzzy-match, agg keywords, time groups, filter ops)               │
    │                                                                        │
    ▼                                                                        │
SQL Builder                    ← low confidence / no match? → LLM Fallback ─┘
  (parameterized, validated)              (GPT-4o-mini, schema-prompted)
    │
    ▼
SQL Validation Layer
  (sqlglot parse · SELECT-only · column allowlist · injection patterns)
    │
    ▼
Query Execution + Cache (TTL 300 s)
    │
    ▼
Result + chart recommendation
```

---

## Features

- **Data Ingestion** — CSV, XLS, XLSX (up to 100 MB); chunked streaming; encoding detection; schema/type inference; background processing with status polling
- **Metadata Engine** — auto column types (numeric, categorical, datetime, boolean), null %, unique count, min/max/mean/std, semantic tags (revenue, date, customer ID …)
- **NLP Query Engine** — 15+ intent patterns; entity/column fuzzy matching; safe parameterized SQL generation; optional GPT-4o-mini fallback; TTL result cache
- **Analytics Engine** — summary stats, correlation matrix, outlier detection (IQR), time-series aggregation, distribution histograms, top-N
- **Dashboard Engine** — full CRUD; AI-driven auto-generation from a prompt; drag-and-drop grid layout (12 columns); per-widget SQL + chart type
- **Reporting Engine** — multi-section reports; execute SQL per section; export to **CSV** and **PDF** (ReportLab)
- **Security** — sqlglot-based SELECT-only guard; column allowlist validation; file size + type enforcement; input sanitisation
- **Performance** — async FastAPI + aiosqlite; chunked pandas ingestion; TTL query cache; background tasks for large uploads

---

## Quick Start — Local Development

### Prerequisites

- Python 3.11+
- Node.js 18+

### Backend

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment (copy and edit)
cp .env.example .env
# Optional: set OPENAI_API_KEY for LLM fallback

# Start the server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

API docs available at: http://localhost:8000/docs

### Frontend

```bash
cd frontend

npm install
npm run dev
```

Open: http://localhost:5173

---

## Quick Start — Docker Compose

```bash
# Optional: set your OpenAI key for LLM fallback
export OPENAI_API_KEY=sk-...

docker compose up --build
```

- Frontend → http://localhost:3000
- Backend API → http://localhost:8000
- API docs → http://localhost:8000/docs

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `sqlite+aiosqlite:///./nlp_platform.db` | SQLAlchemy async DB URL |
| `UPLOAD_DIR` | `./uploads` | Directory for uploaded files |
| `MAX_FILE_SIZE_MB` | `100` | Maximum upload size in MB |
| `CHUNK_SIZE` | `10000` | Pandas read_csv chunk size |
| `OPENAI_API_KEY` | _(empty)_ | OpenAI key; enables LLM SQL fallback when set |
| `OPENAI_MODEL` | `gpt-4o-mini` | OpenAI model for SQL generation |
| `CACHE_TTL_SECONDS` | `300` | Query result cache TTL |
| `CORS_ORIGINS` | `["http://localhost:3000","http://localhost:5173"]` | Allowed CORS origins |
| `LOG_LEVEL` | `INFO` | Loguru log level |
| `DEBUG` | `false` | Enable SQLAlchemy query echo |
| `SECRET_KEY` | _(change me)_ | App secret (JWT-ready) |

---

## API Reference

### Datasets
| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/v1/datasets/upload` | Upload file (multipart/form-data: `file`, `name`) — returns 202 immediately |
| `GET` | `/api/v1/datasets` | List all datasets |
| `GET` | `/api/v1/datasets/{id}` | Get dataset + column metadata |
| `DELETE` | `/api/v1/datasets/{id}` | Delete dataset, file, and data table |
| `GET` | `/api/v1/datasets/{id}/columns` | List columns only |

### NLP Query
| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/v1/query` | NLP query → SQL → results |
| `POST` | `/api/v1/query/sql` | Direct SQL (validated SELECT) |

### Analytics
| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/v1/analytics/{id}/summary` | Summary statistics |
| `GET` | `/api/v1/analytics/{id}/correlations` | Correlation matrix |
| `GET` | `/api/v1/analytics/{id}/timeseries` | Time-series aggregation |
| `GET` | `/api/v1/analytics/{id}/distribution` | Column distribution |
| `GET` | `/api/v1/analytics/{id}/outliers` | Outlier detection (IQR) |

### Dashboards
| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/v1/dashboards` | List dashboards |
| `POST` | `/api/v1/dashboards` | Create dashboard |
| `POST` | `/api/v1/dashboards/generate` | Auto-generate from NLP prompt |
| `GET` | `/api/v1/dashboards/{id}` | Get dashboard + widgets |
| `PUT` | `/api/v1/dashboards/{id}` | Update dashboard |
| `DELETE` | `/api/v1/dashboards/{id}` | Delete dashboard |
| `POST` | `/api/v1/dashboards/{id}/widgets` | Add widget |
| `PUT` | `/api/v1/dashboards/{id}/widgets/{wid}` | Update widget |
| `DELETE` | `/api/v1/dashboards/{id}/widgets/{wid}` | Delete widget |
| `POST` | `/api/v1/dashboards/{id}/widgets/{wid}/data` | Fetch widget data |

### Reports
| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/v1/reports` | List reports |
| `POST` | `/api/v1/reports` | Create report |
| `POST` | `/api/v1/reports/generate` | Create + generate immediately |
| `GET` | `/api/v1/reports/{id}` | Get report + sections |
| `PUT` | `/api/v1/reports/{id}` | Update title/description |
| `DELETE` | `/api/v1/reports/{id}` | Delete report |
| `POST` | `/api/v1/reports/{id}/generate` | Execute section queries |
| `POST` | `/api/v1/reports/{id}/sections` | Add section |
| `GET` | `/api/v1/reports/{id}/export/csv` | Download CSV |
| `GET` | `/api/v1/reports/{id}/export/pdf` | Download PDF |

---

## NLP Query Examples

| Natural language | Generated SQL intent |
|------------------|---------------------|
| `Show top 10 customers by revenue` | `top_n` — GROUP BY + ORDER BY SUM DESC LIMIT 10 |
| `Monthly sales trend` | `trend` — strftime group by month |
| `Average order value by region` | `aggregate` — GROUP BY + AVG |
| `Find orders where status is cancelled` | `filter` — WHERE status = 'cancelled' |
| `How many unique products` | `count` — COUNT(DISTINCT ...) |
| `Correlation between price and quantity` | `correlation` — analytics endpoint |
| `Distribution of customer age` | `distribution` — histogram bins |

---

## Project Structure

```
NLP/
├── backend/
│   ├── app/
│   │   ├── main.py               FastAPI app + lifespan + middleware
│   │   ├── config.py             Pydantic-settings configuration
│   │   ├── database.py           SQLAlchemy async engine + aiosqlite helper
│   │   ├── models/               ORM models (Dataset, Dashboard, Report …)
│   │   ├── schemas/              Pydantic v2 request/response schemas
│   │   ├── core/
│   │   │   ├── security.py       SQL injection guard (sqlglot)
│   │   │   ├── cache.py          TTL in-memory query cache
│   │   │   ├── exceptions.py     Structured app exceptions
│   │   │   └── logging.py        Loguru structured logging setup
│   │   ├── services/
│   │   │   ├── ingestion.py      File upload, chunked CSV/Excel parsing
│   │   │   ├── metadata.py       Auto metadata + semantic tagging
│   │   │   ├── nlp_engine.py     Intent detection + entity extraction
│   │   │   ├── sql_generator.py  Safe parameterized SQL builder
│   │   │   ├── analytics.py      Stats, correlations, outliers, time-series
│   │   │   ├── dashboard_service.py  Dashboard + widget CRUD + NLP generation
│   │   │   └── report_service.py     Report CRUD + CSV/PDF export
│   │   └── api/v1/               REST route handlers
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── App.tsx               Router + layout wrapper
│   │   ├── main.tsx              React entry point
│   │   ├── theme.ts              MUI theme (Inter, rounded, blue/teal)
│   │   ├── types/index.ts        All TypeScript interfaces
│   │   ├── services/api.ts       Axios client + all API functions
│   │   ├── hooks/                useDatasets, useQuery
│   │   ├── components/           Layout, DataUpload, NLPQueryBar, DataTable, Charts, Metadata
│   │   └── pages/                Home, Datasets, Query, Dashboard, Reports
│   ├── package.json
│   ├── Dockerfile
│   └── nginx.conf
├── docker-compose.yml
└── README.md
```

---

## Extending to PostgreSQL

Change `DATABASE_URL` in `.env`:

```
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/nlp_platform
```

Add to requirements: `asyncpg`

No other code changes needed — the SQLAlchemy layer is database-agnostic.

---

## Security Notes

- All NLP-generated SQL passes through `core/security.py` (sqlglot parse → SELECT-only → column allowlist)
- File uploads are validated by extension and size before touching disk
- No raw user strings ever reach the database directly
- JWT authentication hooks are in place (enable via `SECRET_KEY` + middleware)
- CORS locked to configured origins

---

## License

MIT
