#!/bin/bash
set -e
cd "$(dirname "$0")/business_logic_service"
export PYTHONPATH=.
export BACKEND_URL="${BACKEND_URL:-http://localhost:8573}"
exec uvicorn app.main:app --host 0.0.0.0 --port 8531 --reload
