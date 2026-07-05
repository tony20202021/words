#!/bin/bash
# Start Web Frontend on port 8548
set -e
cd "$(dirname "$0")/web_frontend"

export BLS_URL="${BLS_URL:-http://localhost:8531}"
export BACKEND_URL="${BACKEND_URL:-http://localhost:8573}"
export SECRET_KEY="${SECRET_KEY:-change-me-in-production-please}"
export WEB_URL="${WEB_URL:-http://localhost:8548}"

echo "Starting Web Frontend on port 8548..."
conda run -n amikhalev_language_learning_bot \
    uvicorn app.main:app --host 0.0.0.0 --port 8548 --reload
