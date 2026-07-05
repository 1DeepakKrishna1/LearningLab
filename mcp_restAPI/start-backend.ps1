# Start the FastAPI backend (creates venv + installs deps on first run).
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot\backend

if (-not (Test-Path .venv)) {
    Write-Host "Creating virtual environment..."
    python -m venv .venv
    .\.venv\Scripts\python.exe -m pip install --upgrade pip
    .\.venv\Scripts\python.exe -m pip install -r requirements.txt
}

if (-not (Test-Path .env)) {
    Copy-Item .env.example .env
    Write-Host "Created backend\.env - edit it and set OPENAI_API_KEY." -ForegroundColor Yellow
}

.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
