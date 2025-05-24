#!/bin/bash

# Загружаем переменные окружения из .env
if [ -f "./run_export_env.sh" ]; then
    echo "Загрузка переменных окружения..."
    source ./run_export_env.sh
else
    echo "Скрипт exprun_export_envort_env.sh не найден. Используются значения по умолчанию."
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
if [ ! -d "$HOME/mongodb/data" ] || [ ! -d "$HOME/mongodb/log" ] || [ ! -d "$HOME/mongodb/config" ]; then
    echo "Создаем директории для MongoDB..."
    mkdir -p $HOME/mongodb/data
    mkdir -p $HOME/mongodb/log
    mkdir -p $HOME/mongodb/config
fi

# Проверяем наличие конфигурационного файла
if [ ! -f "$HOME/mongodb/config/mongod.conf" ]; then
    echo "Создаем конфигурационный файл mongod.conf..."
    cat > $HOME/mongodb/config/mongod.conf << EOL
storage:
  dbPath: $HOME/mongodb/data
systemLog:
  destination: file
  path: $HOME/mongodb/log/mongod.log
  logAppend: true
net:
  bindIp: $MONGODB_HOST
  port: $MONGODB_PORT
EOL
else
    # Обновляем существующий конфигурационный файл
    echo "Обновляем конфигурационный файл mongod.conf..."
    # Создаем временный файл
    cat > $HOME/mongodb/config/mongod.conf.tmp << EOL
storage:
  dbPath: $HOME/mongodb/data
systemLog:
  destination: file
  path: $HOME/mongodb/log/mongod.log
  logAppend: true
net:
  bindIp: $MONGODB_HOST
  port: $MONGODB_PORT
EOL
    # Заменяем оригинальный файл
    mv $HOME/mongodb/config/mongod.conf.tmp $HOME/mongodb/config/mongod.conf
fi

# Проверяем, установлена ли MongoDB
if [ ! -d "$HOME/mongodb/bin" ] || [ ! -f "$HOME/mongodb/bin/mongod" ]; then
    echo "❌ MongoDB не установлена в директории $HOME/mongodb/bin"
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
$HOME/mongodb/bin/mongod --config $HOME/mongodb/config/mongod.conf --fork

# Проверяем успешность запуска
if [ $? -eq 0 ]; then
    echo "✅ MongoDB успешно запущена на $MONGODB_HOST:$MONGODB_PORT"
    echo "Для остановки MongoDB используйте: pkill -f mongod"
else
    echo "❌ Ошибка при запуске MongoDB"
    echo "Проверьте логи: $HOME/mongodb/log/mongod.log"
fi