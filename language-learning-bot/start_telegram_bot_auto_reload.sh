#!/bin/bash
# Auto-reload Telegram bot on .py file changes (mirrors start_3_frontend_auto_reload.sh pattern)

cleanup_and_exit() {
    echo "Stopping telegram bot watcher..."
    pkill -f "watchmedo auto-restart.*app.main" || true
    exit 0
}
trap cleanup_and_exit SIGINT SIGTERM

cd /home/tony/repos/words/language-learning-bot/telegram_bot

exec /home/tony/miniconda3/envs/amikhalev_language_learning_bot/bin/watchmedo auto-restart \
    --directory=app \
    --directory=../common \
    --pattern="*.py" \
    --recursive \
    -- /home/tony/miniconda3/envs/amikhalev_language_learning_bot/bin/python -m app.main
