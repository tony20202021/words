#!/bin/bash
# Скрипт для экспорта переменных из .env файла в окружение

# Путь к .env файлу
ENV_FILE=".env"

# Проверяем существование файла
if [ ! -f "$ENV_FILE" ]; then
    echo "Файл .env не найден. Используются значения по умолчанию."
    # Устанавливаем значения по умолчанию
    export MONGODB_HOST="localhost"
    export MONGODB_PORT="27027"
    export MONGODB_DB_NAME="language_learning_bot"
    exit 0
fi

# Загружаем переменные из .env файла
echo "Загрузка переменных окружения из .env файла..."

# Загружаем все переменные из файла
while IFS= read -r line; do
    # Пропускаем комментарии и пустые строки
    if [[ ! $line =~ ^# && -n $line ]]; then
        # Не экспортируем строки с комментариями после значения
        if [[ ! $line =~ "#" ]]; then
            export "$line"
        else
            # Экспортируем только часть строки до #
            export "${line%%#*}"
        fi
    fi
done < "$ENV_FILE"

# Проверяем наличие необходимых переменных и устанавливаем значения по умолчанию, если нужно
if [ -z "$MONGODB_HOST" ]; then
    export MONGODB_HOST="localhost"
    echo "MONGODB_HOST не задан, используется значение по умолчанию: localhost"
fi

if [ -z "$MONGODB_PORT" ]; then
    export MONGODB_PORT="27027"
    echo "MONGODB_PORT не задан, используется значение по умолчанию: 27027"
fi

if [ -z "$MONGODB_DB_NAME" ]; then
    export MONGODB_DB_NAME="language_learning_bot"
    echo "MONGODB_DB_NAME не задан, используется значение по умолчанию: language_learning_bot"
fi

echo "Настройки MongoDB:"
echo "Host: $MONGODB_HOST"
echo "Port: $MONGODB_PORT"
echo "Database: $MONGODB_DB_NAME"
echo "Переменные окружения загружены успешно."