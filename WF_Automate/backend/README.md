# Backend - Workflow Management API

This is a simple FastAPI backend to supply dummy data for the workflow management system.

## Installation

```bash
cd backend
python -m venv venv
venv\Scripts\activate  # Windows
pip install -r requirements.txt
```

## Running

```bash
uvicorn app.main:app --reload --port 8000
```

API endpoints:
- `GET /` - health check
- `GET /workflows/` - list workflows
- `GET /workflows/{id}` - get workflow by id
- `POST /workflows/` - create new workflow (send JSON body)
- `PUT /workflows/{id}` - update existing workflow
- `POST /workflows/{id}/clone` - clone an existing workflow
- `POST /workflows/{id}/run` - simulate execution; returns step-by-step results
- `GET /agents/` - list agents
- `GET /agents/{id}` - get agent by id
- `POST /ai/chat` - AI assistant proxy; requires `OPENAI_API_KEY` env var to call actual OpenAI, otherwise returns a stub response

**AI Setup**

To enable real AI responses, set one of the following environment variables with your OpenAI API key (either name works):

```powershell
setx OPENAI_API_KEY "your-key-here"
# or
setx GROQ_API_KEY "your-key-here"
```

Restart the backend server after setting the key. The `/ai/chat` endpoint will forward messages to the OpenAI ChatCompletion API.

This setup returns dummy static data to simulate backend responses.
