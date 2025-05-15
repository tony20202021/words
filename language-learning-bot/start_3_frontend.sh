#!/bin/bash
# Проверка, запущен ли уже процесс фронтенда
PID_FILE=".frontend.pid"
APP_NAME="--process-name=frontend"

# Функция для поиска и завершения всех процессов фронтенда
cleanup_frontend_processes() {
    echo "Поиск и завершение всех процессов фронтенда..."
    
    # Находим процессы по уникальному идентификатору
    # Обратите внимание на экранирование параметра перед передачей в grep
    FRONTEND_PIDS=$(ps aux | grep -v grep | grep -e "${APP_NAME}" | awk '{print $2}')
    
    # Выводим информацию о найденных процессах
    if [ ! -z "$FRONTEND_PIDS" ]; then
        echo "Найдены процессы фронтенда:"
        for pid in $FRONTEND_PIDS; do
            ps -p $pid -o pid,ppid,cmd,%cpu,%mem --no-headers
        done
        
        echo "Завершение процессов..."
        for pid in $FRONTEND_PIDS; do
            kill $pid 2>/dev/null
        done
        sleep 2
        
        # Проверяем, остались ли процессы и завершаем принудительно
        REMAINING=""
        for pid in $FRONTEND_PIDS; do
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
        echo "Все процессы фронтенда завершены"
    else
        echo "Активные процессы фронтенда не найдены"
    fi
}

# Обработчик сигнала для корректного завершения
cleanup_and_exit() {
    echo "Получен сигнал завершения. Останавливаем фронтенд..."
    cleanup_frontend_processes
    rm -f "$PID_FILE"
    exit 0
}

# Установка обработчиков сигналов
trap cleanup_and_exit SIGINT SIGTERM

# Выполняем очистку процессов при запуске
echo "Проверка наличия запущенных экземпляров фронтенда..."
cleanup_frontend_processes

# Удаляем старый PID-файл, если он существует
if [ -f "$PID_FILE" ]; then
    rm "$PID_FILE"
    echo "Старый PID-файл удален"
fi

# Запуск фронтенда
cd frontend
echo "Запуск фронтенда..."
echo $$ > "../$PID_FILE"  # Сохраняем PID текущего процесса
echo "PID текущего процесса: $$"
echo "Фронтенд запускается. Нажмите Ctrl+C для завершения."

# Запускаем процесс python с идентификатором
python -m app.main_frontend "$APP_NAME"

# Этот код выполнится только если python завершится сам
echo "Процесс фронтенда завершился."
cleanup_frontend_processes
rm -f "$PID_FILE"


# TODO в отдельном фйале - сделать скрипт для перезапуска сервиса после обновления файлов

# pip install watchdog

# from watchdog.observers import Observer
# from watchdog.events import FileSystemEventHandler
# import time
# import subprocess
# import os

# class ReloadHandler(FileSystemEventHandler):
#     def on_modified(self, event):
#         print(f"Изменен файл: {event.src_path}")
#         subprocess.Popen(["python", "your_script.py"])

# if __name__ == "__main__":
#     path = "."  # Текущая директория
#     event_handler = ReloadHandler()
#     observer = Observer()
#     observer.schedule(event_handler, path, recursive=True)
#     observer.start()

#     try:
#         while True:
#             time.sleep(1)
#     except KeyboardInterrupt:
#         observer.stop()
#     observer.join()