#!/bin/bash
set -e
cd "$(dirname "$0")/business_logic_service"
export PYTHONPATH=.
export BACKEND_URL="${BACKEND_URL:-http://localhost:8500}"
export WRITING_IMAGES_URL="${WRITING_IMAGES_URL:-http://localhost:8600}"
exec uvicorn app.main:app --host 0.0.0.0 --port 8700 --reload
