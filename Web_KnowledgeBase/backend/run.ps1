# Backend dev server (Windows PowerShell)
if (-not (Test-Path ".venv")) {
    python -m venv .venv
}
. .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
if (-not (Test-Path ".env")) {
    Copy-Item .env.example .env
    Write-Host "Created .env from template — add your OPENAI_API_KEY before querying." -ForegroundColor Yellow
}
uvicorn app.main:app --reload --port 9000
