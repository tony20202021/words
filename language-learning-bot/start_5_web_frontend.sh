#!/bin/bash
set -e
cd "$(dirname "$0")/web_frontend"
export PYTHONPATH=.
export BLS_URL="${BLS_URL:-http://localhost:8700}"
exec uvicorn app.main:app --host 0.0.0.0 --port 8800 --reload
