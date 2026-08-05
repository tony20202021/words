#!/bin/bash
# Ручной запуск бэкенда с автоперезапуском при изменении файлов.
# В проде бэкенд поднимает systemd (langbot-backend.service) той же командой.
#
# Раньше скрипт звал frontend/app/watch_and_reload.py из легаси-фронтенда;
# фронтенд удалён, перезапуск делает штатный --reload uvicorn.
set -e

cd "$(dirname "$0")/backend"

export PYTHONPATH=.
export MONGODB_URL="${MONGODB_URL:-mongodb://localhost:8527}"
export MONGODB_DB_NAME="${MONGODB_DB_NAME:-language_learning_bot}"

exec uvicorn app.main_backend:app \
    --host 0.0.0.0 --port 8573 \
    --reload --reload-dir app --reload-dir conf
