#!/bin/bash
# Скрипт запуска сервиса генерации картинок написания
PID_FILE=".writing_service.pid"
APP_NAME="--process-name=writing_service"

# Функция для поиска и завершения всех процессов сервиса картинок
cleanup_writing_service_processes() {
    echo "Поиск и завершение всех процессов сервиса картинок..."
    
    # Находим процессы по уникальному идентификатору
    WRITING_SERVICE_PIDS=$(ps aux | grep -v grep | grep -e "${APP_NAME}" | awk '{print $2}')
    
    # Выводим информацию о найденных процессах
    if [ ! -z "$WRITING_SERVICE_PIDS" ]; then
        echo "Найдены процессы сервиса картинок:"
        for pid in $WRITING_SERVICE_PIDS; do
            ps -p $pid -o pid,ppid,cmd,%cpu,%mem --no-headers
        done
        
        echo "Завершение процессов..."
        for pid in $WRITING_SERVICE_PIDS; do
            kill $pid 2>/dev/null
        done
        sleep 2
        
        # Проверяем, остались ли процессы и завершаем принудительно
        REMAINING=""
        for pid in $WRITING_SERVICE_PIDS; do
            if ps -p $pid > /dev/null; then
                REMAINING="$REMAINING $pid"
            fi
        done
        
        if [ ! -z "$REMAINING" ]; then
            echo "Принудительное завершение оставшихся процессов:"
            for pid in $REMAINING; do
                ps -p $pid -o pid,ppid,cmd,%cpu,%mem --no-headers
                kill -9 $pid 2>/dev/null
            done
        fi
        echo "Все процессы сервиса картинок завершены"
    else
        echo "Активные процессы сервиса картинок не найдены"
    fi
}

# Функция для корректного завершения
cleanup_and_exit() {
    echo "Получен сигнал завершения. Останавливаем сервис картинок..."
    cleanup_writing_service_processes
    rm -f "$PID_FILE"
    exit 0
}

# Установка обработчиков сигналов
trap cleanup_and_exit SIGINT SIGTERM

# Проверка наличия запущенных экземпляров сервиса
echo "Проверка наличия запущенных экземпляров сервиса картинок..."
cleanup_writing_service_processes

# Удаляем старый PID-файл, если он существует
if [ -f "$PID_FILE" ]; then
    rm "$PID_FILE"
    echo "Старый PID-файл удален"
fi

# Запуск сервиса картинок
cd writing_service
echo "Запуск сервиса генерации картинок написания..."
echo $$ > "../$PID_FILE"  # Сохраняем PID текущего процесса
echo "PID текущего процесса: $$"
echo "Сервис картинок запускается. Нажмите Ctrl+C для завершения."

# Запускаем процесс python с идентификатором
# Порт и auto-reload определяются в конфигурации Hydra и uvicorn
python -m app.main_writing_service "$APP_NAME"

# Этот код выполнится только если python завершится сам
echo "Процесс сервиса картинок завершился."
cleanup_writing_service_processes
rm -f "$PID_FILE"
