#!/bin/bash

# Загружаем переменные окружения из .env
if [ -f "./export_env.sh" ]; then
    echo "Загрузка переменных окружения..."
    source ./export_env.sh
else
    echo "Скрипт export_env.sh не найден. Используются значения по умолчанию."
    export MONGODB_HOST="localhost"
    export MONGODB_PORT="27027"
fi

# Выводим информацию о настройках MongoDB
echo "Настройки MongoDB:"
echo "Хост: $MONGODB_HOST"
echo "Порт: $MONGODB_PORT"

# Проверяем, не запущен ли уже MongoDB
if pgrep -x "mongod" > /dev/null; then
    echo "MongoDB уже запущен"
    exit 0
fi

# Проверяем наличие директорий для MongoDB
if [ ! -d "/workspace-SR006.nfs2/amikhalev/mongodb/data" ] || [ ! -d "/workspace-SR006.nfs2/amikhalev/mongodb/log" ] || [ ! -d "/workspace-SR006.nfs2/amikhalev/mongodb/config" ]; then
    echo "Создаем директории для MongoDB..."
    mkdir -p /workspace-SR006.nfs2/amikhalev/mongodb/data
    mkdir -p /workspace-SR006.nfs2/amikhalev/mongodb/log
    mkdir -p /workspace-SR006.nfs2/amikhalev/mongodb/config
fi

# Проверяем наличие конфигурационного файла
if [ ! -f "/workspace-SR006.nfs2/amikhalev/mongodb/config/mongod.conf" ]; then
    echo "Создаем конфигурационный файл mongod.conf..."
    cat > /workspace-SR006.nfs2/amikhalev/mongodb/config/mongod.conf << EOL
storage:
  dbPath: /workspace-SR006.nfs2/amikhalev/mongodb/data
systemLog:
  destination: file
  path: /workspace-SR006.nfs2/amikhalev/mongodb/log/mongod.log
  logAppend: true
net:
  bindIp: $MONGODB_HOST
  port: $MONGODB_PORT
EOL
else
    # Обновляем существующий конфигурационный файл
    echo "Обновляем конфигурационный файл mongod.conf..."
    # Создаем временный файл
    cat > /workspace-SR006.nfs2/amikhalev/mongodb/config/mongod.conf.tmp << EOL
storage:
  dbPath: /workspace-SR006.nfs2/amikhalev/mongodb/data
systemLog:
  destination: file
  path: /workspace-SR006.nfs2/amikhalev/mongodb/log/mongod.log
  logAppend: true
net:
  bindIp: $MONGODB_HOST
  port: $MONGODB_PORT
EOL
    # Заменяем оригинальный файл
    mv /workspace-SR006.nfs2/amikhalev/mongodb/config/mongod.conf.tmp /workspace-SR006.nfs2/amikhalev/mongodb/config/mongod.conf
fi

# Проверяем, установлена ли MongoDB
if [ ! -d "/workspace-SR006.nfs2/amikhalev/mongodb/bin" ] || [ ! -f "/workspace-SR006.nfs2/amikhalev/mongodb/bin/mongod" ]; then
    echo "❌ MongoDB не установлена в директории /workspace-SR006.nfs2/amikhalev/mongodb/bin"
    echo "Пожалуйста, следуйте инструкциям по установке MongoDB в документации"
    exit 1
fi

# Проверяем занятость порта
if lsof -i :$MONGODB_PORT > /dev/null; then
    echo "❌ Порт $MONGODB_PORT уже используется другим процессом"
    echo "Пожалуйста, укажите другой порт в .env файле (MONGODB_PORT=другой_порт)"
    exit 1
fi

# Запускаем MongoDB
echo "Запускаем MongoDB на $MONGODB_HOST:$MONGODB_PORT..."
/workspace-SR006.nfs2/amikhalev/mongodb/bin/mongod --config /workspace-SR006.nfs2/amikhalev/mongodb/config/mongod.conf --fork

# Проверяем успешность запуска
if [ $? -eq 0 ]; then
    echo "✅ MongoDB успешно запущена на $MONGODB_HOST:$MONGODB_PORT"
    echo "Для остановки MongoDB используйте: pkill -f mongod"
else
    echo "❌ Ошибка при запуске MongoDB"
    echo "Проверьте логи: /workspace-SR006.nfs2/amikhalev/mongodb/log/mongod.log"
fi