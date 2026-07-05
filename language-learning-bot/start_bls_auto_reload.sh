#!/bin/bash
# Auto-reload BLS on .py file changes (same pattern as start_telegram_bot_auto_reload.sh)

cleanup_and_exit() {
    echo "Stopping BLS watcher..."
    kill $CHILD_PID 2>/dev/null || true
    exit 0
}
trap cleanup_and_exit SIGINT SIGTERM

cd /home/tony/repos/words/language-learning-bot/business_logic_service

exec /home/tony/miniconda3/envs/amikhalev_language_learning_bot/bin/watchmedo auto-restart \
    --directory=app \
    --directory=../common \
    --pattern="*.py" \
    --recursive \
    -- /home/tony/miniconda3/envs/amikhalev_language_learning_bot/bin/uvicorn \
        app.main:app --host 0.0.0.0 --port 8531
