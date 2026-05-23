#!/bin/bash
# Start Web Frontend on port 8800
set -e
cd "$(dirname "$0")/web_frontend"

export BLS_URL="${BLS_URL:-http://localhost:8700}"
export BACKEND_URL="${BACKEND_URL:-http://localhost:8500}"
export SECRET_KEY="${SECRET_KEY:-change-me-in-production-please}"
export WEB_URL="${WEB_URL:-http://localhost:8800}"

echo "Starting Web Frontend on port 8800..."
conda run -n amikhalev_language_learning_bot \
    uvicorn app.main:app --host 0.0.0.0 --port 8800 --reload
