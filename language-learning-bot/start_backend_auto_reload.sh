#!/bin/bash
# Auto-reload backend on .py file changes (same pattern as start_bls_auto_reload.sh).
#
# Зачем. Три сервиса из четырёх перезапускались сами, а бэкенд — нет, и каждая
# правка в нём (или в common, откуда он берёт версию) требовала sudo. Права
# приходилось выдавать и отзывать ради одного systemctl restart.

cleanup_and_exit() {
    echo "Stopping backend watcher..."
    kill $CHILD_PID 2>/dev/null || true
    exit 0
}
trap cleanup_and_exit SIGINT SIGTERM

cd /home/tony/repos/words/language-learning-bot/backend

exec /home/tony/miniconda3/envs/amikhalev_language_learning_bot/bin/watchmedo auto-restart \
    --directory=app \
    --directory=../common \
    --pattern="*.py" \
    --recursive \
    -- /home/tony/miniconda3/envs/amikhalev_language_learning_bot/bin/uvicorn \
        app.main_backend:app --host 0.0.0.0 --port 8573
