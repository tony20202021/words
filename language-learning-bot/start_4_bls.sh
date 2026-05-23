#!/bin/bash
# Start Business Logic Service (BLS) on port 8700
set -e
cd "$(dirname "$0")/business_logic_service"

export BACKEND_URL="${BACKEND_URL:-http://localhost:8500}"
export TELEGRAM_BOT_TOKEN="${TELEGRAM_BOT_TOKEN:-}"

echo "Starting BLS on port 8700..."
conda run -n amikhalev_language_learning_bot \
    uvicorn app.main:app --host 0.0.0.0 --port 8700 --reload
