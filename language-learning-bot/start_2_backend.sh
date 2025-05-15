#!/bin/bash
# Проверка, запущен ли уже процесс бэкенда
PID_FILE=".backend.pid"
APP_NAME="--process-name=backend"

# Функция для поиска и завершения всех процессов бэкенда
cleanup_backend_processes() {
    echo "Поиск и завершение всех процессов бэкенда..."
    
    # Находим процессы по уникальному идентификатору
    # Обратите внимание на экранирование параметра перед передачей в grep
    BACKEND_PIDS=$(ps aux | grep -v grep | grep -e "${APP_NAME}" | awk '{print $2}')
    
    # Выводим информацию о найденных процессах
    if [ ! -z "$BACKEND_PIDS" ]; then
        echo "Найдены процессы бэкенда:"
        for pid in $BACKEND_PIDS; do
            ps -p $pid -o pid,ppid,cmd,%cpu,%mem --no-headers
        done
        
        echo "Завершение процессов..."
        for pid in $BACKEND_PIDS; do
            kill $pid 2>/dev/null
        done
        sleep 2
        
        # Проверяем, остались ли процессы и завершаем принудительно
        REMAINING=""
        for pid in $BACKEND_PIDS; do
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
        echo "Все процессы бэкенда завершены"
    else
        echo "Активные процессы бэкенда не найдены"
    fi
}

# Функция для корректного завершения
cleanup_and_exit() {
    echo "Получен сигнал завершения. Останавливаем бэкенд..."
    cleanup_backend_processes
    rm -f "$PID_FILE"
    exit 0
}

# Установка обработчиков сигналов
trap cleanup_and_exit SIGINT SIGTERM

# Проверка наличия запущенных экземпляров бэкенда
echo "Проверка наличия запущенных экземпляров бэкенда..."
cleanup_backend_processes

# Удаляем старый PID-файл, если он существует
if [ -f "$PID_FILE" ]; then
    rm "$PID_FILE"
    echo "Старый PID-файл удален"
fi

# Запуск бэкенда
cd backend
echo "Запуск бэкенда..."
echo $$ > "../$PID_FILE"  # Сохраняем PID текущего процесса
echo "PID текущего процесса: $$"
echo "Бэкенд запускается. Нажмите Ctrl+C для завершения."

# Запускаем процесс python с идентификатором
# Порт теперь определяется в конфигурации Hydra и не передается как параметр
python -m app.main_backend "$APP_NAME"

# Этот код выполнится только если python завершится сам
echo "Процесс бэкенда завершился."
cleanup_backend_processes
rm -f "$PID_FILE"