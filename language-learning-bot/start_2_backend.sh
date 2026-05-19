#!/bin/bash
# Запуск бэкенда с автоматическим перезапуском при изменении файлов

cleanup_and_exit() {
    echo "Получен сигнал завершения. Останавливаем бэкенд..."
    pkill -f "watch_and_reload.py.*backend_autoreload" 2>/dev/null
    exit 0
}

trap cleanup_and_exit SIGINT SIGTERM

if [ ! -f "frontend/app/watch_and_reload.py" ]; then
    echo "frontend/app/watch_and_reload.py не найден"
    exit 1
fi

echo "Запуск бэкенда с автоматическим перезапуском..."

cd backend

python ../frontend/app/watch_and_reload.py \
    --script app/main_backend.py \
    --paths app ./conf/config \
    --process-name backend_autoreload \
    --extensions .py .yaml .yml .json \
    --ignore-dirs __pycache__ .git env venv .env .venv logs

wait
echo "Автоматический перезапуск бэкенда остановлен."
