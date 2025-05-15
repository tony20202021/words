#!/bin/bash
# Скрипт для запуска автоматического перезапуска фронтенда при изменении файлов

# Обработчик сигналов для корректного завершения
cleanup_and_exit() {
    echo "Получен сигнал завершения. Останавливаем процессы..."
    
    # Находим и останавливаем процессы Python
    pkill -f "python watch_and_reload.py"
    
    exit 0
}

# Установка обработчиков сигналов
trap cleanup_and_exit SIGINT SIGTERM

# Проверяем наличие скрипта для автоматического перезапуска
if [ ! -f "frontend/app/watch_and_reload.py" ]; then
    echo "Скрипт frontend/app/watch_and_reload.py не найден. Создайте его"
    exit 1
fi

echo "Запуск автоматического перезапуска..."

# Запускаем скрипт автоматического перезапуска
python frontend/app/watch_and_reload.py \
    --script frontend/app/main_frontend.py \
    --paths frontend/app frontend/conf/config \
    --process-name frontend_autoreload \
    --extensions .py .yaml .yml .json \
    --ignore-dirs __pycache__ .git env venv .env .venv logs

# Ожидаем завершения, это необходимо для корректной обработки сигналов
wait

echo "Автоматический перезапуск остановлен."