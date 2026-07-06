# Precision QA - Backend

This is a minimal FastAPI backend scaffold.

Install and run (Windows PowerShell):

```powershell
cd c:\allCode\code_DK\PQA\precision-qa-backend
python -m pip install -r requirements.txt
uvicorn main:app --reload
```

Endpoints:
- GET / -> returns a simple ping message
- GET /external -> fetches https://httpbin.org/get via httpx

LLM (Groq) integration
----------------------
This project can call a Groq LLM provider using either the `langchain_groq` SDK or a raw HTTP endpoint. Configure via environment variables (see `.env.example`):

- `GROQ_API_KEY` - your Groq API key
- `GROQ_ENDPOINT` - HTTP endpoint for Groq inference (if not using SDK)
- `GROQ_MODEL` - model name (default `llama-3.3-70b-versatile`)
- `GROQ_MAX_TOKENS` - max tokens for LLM (default `1000`)
- `GROQ_TEMPERATURE` - temperature (default `0`)
- `ALLOWED_ORIGINS` - comma-separated list of allowed CORS origins (default `http://localhost:3000`)

If `langchain_groq` is installed and available, the backend will attempt to call `ChatGroq(model=..., max_tokens=..., temperature=...)`. If not available, it will POST JSON `{prompt, max_tokens, temperature}` to `GROQ_ENDPOINT` with an Authorization header.

Make sure to install and configure any provider SDK you use. If you provide an exact SDK snippet (imports and call pattern), I can wire the backend to use it precisely.
