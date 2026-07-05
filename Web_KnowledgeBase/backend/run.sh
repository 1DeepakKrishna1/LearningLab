#!/usr/bin/env bash
# Backend dev server (macOS/Linux)
set -e
cd "$(dirname "$0")"
[ -d .venv ] || python3 -m venv .venv
# shellcheck disable=SC1091
source .venv/bin/activate
pip install -r requirements.txt
[ -f .env ] || { cp .env.example .env; echo "Created .env — add your OPENAI_API_KEY."; }
uvicorn app.main:app --reload --port 9000
