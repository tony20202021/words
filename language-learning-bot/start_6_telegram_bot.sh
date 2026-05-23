#!/bin/bash
# Start new Telegram Bot (thin client for BLS)
set -e
cd "$(dirname "$0")/telegram_bot"

export BOT_TOKEN="${BOT_TOKEN:-}"
export BLS_URL="${BLS_URL:-http://localhost:8700}"

if [ -z "$BOT_TOKEN" ]; then
    echo "ERROR: BOT_TOKEN env var is not set"
    exit 1
fi

echo "Starting Telegram Bot..."
conda run -n amikhalev_language_learning_bot python -m app.main
