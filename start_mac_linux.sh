#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"
[ -f backend/.env ] || cp backend/.env.example backend/.env
[ -d backend/.venv ] || python3 -m venv backend/.venv
backend/.venv/bin/pip install -r backend/requirements.txt
(cd backend && .venv/bin/uvicorn app.main:app --reload --port 8000) &
(cd frontend && npm install && npm run dev)
