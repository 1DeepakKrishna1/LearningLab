# Precision QA - Monorepo

This workspace contains two minimal projects:

- `precision-qa-ui` - React frontend scaffold
- `precision-qa-backend` - FastAPI backend scaffold

Quick start (Windows PowerShell):

1) Frontend

```powershell
cd c:\allCode\code_DK\PQA\precision-qa-ui
npm install
npm start
```

# Precision QA - Monorepo

This repository contains two apps in a single workspace:

- `precision-qa-ui` — React frontend (Create React App + Tailwind)
- `precision-qa-backend` — FastAPI backend (uvicorn)

Minimum environment (Windows)
- Node.js + npm (for the frontend)
- Python 3.10+ and pip (for the backend)

Run locally (PowerShell)

1) Frontend

```powershell
cd c:\allCode\code_DK\PQA\precision-qa-ui
npm install
npm start
```

The frontend dev server runs by default at http://localhost:3100. Port configuration is controlled by the `.env` file.

2) Backend

```powershell
cd c:\allCode\code_DK\PQA\precision-qa-backend
python -m pip install -r requirements.txt
python main.py
```

OR: manually provide the port in cmdlet
uvicorn main:app --reload --host 127.0.0.1 --port 8100

The backend API runs on http://127.0.0.1:8100 by default. Port configuration is controlled by the `.env` file. The OpenAPI docs are available at `/docs` when the server is running.

## Port Configuration

Both frontend and backend ports are configurable via environment variables:

**Backend (.env file in precision-qa-backend/):**
```
BACKEND_PORT=8100
FRONTEND_PORT=3100
ALLOWED_ORIGINS=http://localhost:3100
```

**Frontend (.env file in precision-qa-ui/):**
```
PORT=3100
REACT_APP_API_BASE=http://localhost:8100
```

API contract (current canonical shape)
- Endpoint: POST `/evaluate-answers`
	- Request body (JSON):

```json
{
	"statement": "<user statement text>",
	"qa": [
		{ "question": "Question text 1", "answer": "Answer text 1", "category": "Optional category" },
		{ "question": "Question text 2", "answer": "Answer text 2" }
	]
}
```

	- Response body (JSON):

```json
{
	"evaluations": [
		{ "question": "...", "answer": "...", "rating": 7, "explanation": "...", "next_questions": ["...", "..."] }
	]
}
```

- Endpoint: POST `/final-evaluation`
	- Request body (JSON): same `{ statement, qa }` payload shape.
	- Response body (JSON):

```json
{
	"answers": [ { "question": "...", "answer": "...", "rating": 8, "explanation": "..." } ],
	"readiness_score": 80,
	"recommendations": ["...", "..."]
}
```

Notes and guidance
- The frontend is already wired to send `{ statement, qa }` from the UI flow.
- The backend now uses `qa` everywhere — legacy `answers` handling was removed.
- LLM integration (Groq) is optional: the backend contains deterministic fallback logic so the app works without an LLM configured. If you want real LLM outputs, set the environment variables `GROQ_API_KEY` and `GROQ_ENDPOINT` (or install the SDK and configure `GROQ_MODEL`, etc.) — see `precision-qa-backend/.env.example` for guidance.

Quick test examples (PowerShell)

Create a payload file and POST it to the running backend (avoids PowerShell quoting issues):

```powershell
$payload = @'
{"statement":"Test statement","qa":[{"question":"Q1","answer":"A short answer"},{"question":"Q2","answer":""}]}
'@
$path = Join-Path $env:TEMP 'qa_payload.json'
Set-Content -Path $path -Value $payload -Encoding UTF8

# Evaluate
Invoke-RestMethod -Uri 'http://127.0.0.1:8100/evaluate-answers' -Method POST -InFile $path -ContentType 'application/json' | ConvertTo-Json -Depth 5

# Final evaluation
Invoke-RestMethod -Uri 'http://127.0.0.1:8100/final-evaluation' -Method POST -InFile $path -ContentType 'application/json' | ConvertTo-Json -Depth 5

Remove-Item $path -Force
```

If you want me to also update `precision-qa-backend/README.md` or add unit tests for the request/response shapes, I can do that next.
