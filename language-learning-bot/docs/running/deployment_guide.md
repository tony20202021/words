# Руководство по развертыванию Language Learning Bot

## Содержание
1. [Обзор взаимодействия компонентов](#обзор-взаимодействия-компонентов)
2. [Последовательность действий при развертывании](#последовательность-действий-при-развертывании)
3. [Администрирование системы](#администрирование-системы)
4. [Обслуживание приложения](#обслуживание-приложения)
5. [Устранение неполадок](#устранение-неполадок)
6. [Обновление приложения](#обновление-приложения)

## Обзор взаимодействия компонентов

Архитектура системы предусматривает взаимодействие следующих компонентов:

1. **Скрипт run_export_env.sh** загружает настройки из файла `.env`
   - Экспортирует переменные `MONGODB_HOST`, `MONGODB_PORT` и `MONGODB_DB_NAME` 
   - Устанавливает значения по умолчанию для отсутствующих переменных

2. **Скрипт start_1_db.sh** запускает MongoDB
   - Использует скрипт `run_export_env.sh` для загрузки настроек
   - Создает/обновляет конфигурационный файл MongoDB с актуальными настройками
   - Запускает MongoDB сервер в фоновом режиме

3. **Скрипт start_2_backend.sh** запускает бэкенд
   - Проверяет занятость порта и предлагает альтернативный при необходимости
   - Запускает Python-модуль с параметром `--process-name=backend`
   - Сохраняет PID процесса для последующего управления

4. **Скрипт start_3_frontend.sh** запускает фронтенд
   - Проверяет и завершает конфликтующие процессы фронтенда
   - Запускает Python-модуль с параметром `--process-name=frontend`
   - Сохраняет PID процесса для последующего управления

5. **Скрипт run_tests.sh** запускает тесты приложения
   - Поддерживает различные параметры запуска (тесты компонентов, отчеты о покрытии и т.д.)

## Последовательность действий при развертывании

### 1. Подготовка окружения

1. **Клонирование репозитория**:
   ```bash
   git clone https://github.com/username/language-learning-bot.git
   cd language-learning-bot
   ```

2. **Создание и активация Conda-окружения**:
   ```bash
   conda env create -f environment.yml
   conda activate language-learning-bot
   ```

3. **Настройка переменных окружения**:
   ```bash
   # Копирование шаблона .env файла
   cp .env.example .env
   
   # Редактирование .env файла
   nano .env
   ```

   Минимальное содержимое `.env` файла:
   ```
   MONGODB_HOST=localhost
   MONGODB_PORT=27017
   MONGODB_DB_NAME=language_learning_bot
   TELEGRAM_BOT_TOKEN=your_bot_token_here
   ```

### 2. Настройка MongoDB

1. **Установка MongoDB без прав суперпользователя** (если необходимо):
   ```bash
   # Создание директорий для MongoDB
   mkdir -p ~/mongodb/data ~/mongodb/log ~/mongodb/config ~/mongodb/bin
   
   # Скачивание и установка MongoDB
   cd ~/Downloads
   wget https://fastdl.mongodb.org/linux/mongodb-linux-x86_64-ubuntu2204-7.0.5.tgz
   tar -zxvf mongodb-linux-x86_64-ubuntu2204-7.0.5.tgz
   cp -R mongodb-linux-x86_64-ubuntu2204-7.0.5/bin/* ~/mongodb/bin/
   
   # Добавление MongoDB в PATH
   echo 'export PATH=~/mongodb/bin:$PATH' >> ~/.bashrc
   source ~/.bashrc
   ```

2. **Подготовка скриптов для запуска**:
   ```bash
   # Сделать скрипты исполняемыми
   chmod +x run_export_env.sh start_1_db.sh start_2_backend.sh start_3_frontend.sh run_tests.sh
   ```

### 3. Настройка конфигурации Hydra

1. **Фронтенд** - отредактируйте файлы в директории `frontend/conf/config/`:
   - `bot.yaml` - укажите токен Telegram-бота:
     ```yaml
     token: "YOUR_TELEGRAM_BOT_TOKEN"
     ```
   - `api.yaml` - настройте подключение к бэкенду:
     ```yaml
     base_url: "http://localhost:8500"
     ```

2. **Бэкенд** - отредактируйте файлы в директории `backend/conf/config/`:
   - `api.yaml` - настройте параметры API:
     ```yaml
     host: "0.0.0.0"
     port: 8500
     ```
   - `database.yaml` - настройте подключение к MongoDB:
     ```yaml
     mongodb:
       host: "localhost"
       port: 27017
       db_name: "language_learning_bot"
     ```

### 4. Запуск компонентов

1. **Запуск MongoDB**:
   ```bash
   ./start_1_db.sh
   ```

2. **Инициализация базы данных**:
   ```bash
   python scripts/init_db.py
   ```

3. **Запуск бэкенда**:
   ```bash
   ./start_2_backend.sh
   ```

4. **Запуск фронтенда**:
   ```bash
   ./start_3_frontend.sh
   ```

### 5. Проверка запущенных процессов

```bash
# Проверка MongoDB
ps aux | grep mongod

# Проверка бэкенда
ps aux | grep -e "--process-name=backend"

# Проверка фронтенда
ps aux | grep -e "--process-name=frontend"
```

## Администрирование системы

### Работа с пользователями и администраторами

В проекте реализован скрипт `admin_manager.py` для управления администраторами. Он позволяет:

1. Просматривать список всех пользователей
2. Искать пользователя по Telegram ID
3. Просматривать детальную информацию о пользователе
4. Назначать пользователя администратором

Скрипт работает через API клиент, используя тот же интерфейс, что и бот, и не требует прямого доступа к базе данных.

#### Использование скрипта управления администраторами

```bash
# Вывести справку по командам
python scripts/admin_manager.py --help

# Получить список пользователей
python scripts/admin_manager.py list

# Искать пользователя по Telegram ID
python scripts/admin_manager.py find 123456789

# Сделать пользователя администратором
python scripts/admin_manager.py make-admin user_id_123
```

### Администрирование базы данных

1. **Заполнение базы тестовыми данными**:
   ```bash
   python scripts/seed_data.py
   ```

2. **Резервное копирование**:
   ```bash
   # Создание директории для резервных копий
   mkdir -p backup
   
   # Создание резервной копии
   ~/mongodb/bin/mongodump --host $MONGODB_HOST --port $MONGODB_PORT \
     --db $MONGODB_DB_NAME --out backup/$(date +%Y%m%d)
   ```

3. **Восстановление из резервной копии**:
   ```bash
   # Восстановление из резервной копии
   ~/mongodb/bin/mongorestore --host $MONGODB_HOST --port $MONGODB_PORT \
     --db $MONGODB_DB_NAME backup/YYYYMMDD/$MONGODB_DB_NAME
   ```

4. **Прямой доступ к базе данных** (для отладки):
   ```bash
   # Запуск MongoDB Shell
   ~/mongodb/bin/mongosh
   
   # Подключение к базе данных
   > use language_learning_bot
   
   # Просмотр коллекций
   > show collections
   
   # Пример запроса
   > db.languages.find()
   ```

## Обслуживание приложения

### Перезапуск компонентов

Для перезапуска компонентов системы используйте следующие команды:

```bash
# Перезапуск MongoDB
pkill -f mongod
./start_1_db.sh

# Перезапуск бэкенда
pkill -f -- "--process-name=backend"
./start_2_backend.sh

# Перезапуск фронтенда
pkill -f -- "--process-name=frontend"
./start_3_frontend.sh
```

### Обновление конфигурации

После изменения конфигурационных файлов Hydra необходимо перезапустить соответствующие компоненты:

1. Изменения в `bot.yaml`, `api.yaml` (на стороне клиента), `learning.yaml` - перезапуск фронтенда
2. Изменения в `api.yaml` (на стороне сервера), `database.yaml` - перезапуск бэкенда

### Мониторинг логов

Для мониторинга логов компонентов системы:

```bash
# Логи MongoDB
tail -f ~/mongodb/log/mongod.log

# Логи бэкенда
tail -f backend/logs/backend.log

# Логи фронтенда
tail -f frontend/logs/app.log
```

### Контроль потребления ресурсов

```bash
# Просмотр использования CPU и памяти
ps -o pid,cmd,%cpu,%mem -p $(pgrep -f mongod) $(pgrep -f -- "--process-name=backend") $(pgrep -f -- "--process-name=frontend")

# Мониторинг в реальном времени
top -p $(pgrep -f mongod),$(pgrep -f -- "--process-name=backend"),$(pgrep -f -- "--process-name=frontend")
```

## Устранение неполадок

### Проблемы с MongoDB

1. **MongoDB не запускается**:
   - Проверьте логи: `cat ~/mongodb/log/mongod.log`
   - Убедитесь, что директория данных существует: `ls -la ~/mongodb/data`
   - Проверьте, не занят ли порт: `lsof -i :27017`

2. **Ошибки подключения к MongoDB**:
   - Проверьте, запущен ли сервер: `pgrep -f mongod`
   - Проверьте настройки подключения в `.env` и `database.yaml`
   - Попробуйте подключиться вручную: `~/mongodb/bin/mongosh --host localhost --port 27017`

### Проблемы с бэкендом

1. **Бэкенд не запускается**:
   - Проверьте логи: `cat backend/logs/backend.log`
   - Проверьте, не занят ли порт: `lsof -i :8500`
   - Проверьте настройки подключения к MongoDB

2. **API не отвечает**:
   - Проверьте, запущен ли процесс: `ps aux | grep -e "--process-name=backend"`
   - Проверьте доступность API: `curl http://localhost:8500/api/health`
   - Проверьте логи на наличие ошибок

### Проблемы с фронтендом

1. **Telegram-бот не отвечает**:
   - Проверьте, запущен ли процесс: `ps aux | grep -e "--process-name=frontend"`
   - Проверьте подключение к бэкенду в `api.yaml`
   - Проверьте токен бота в `bot.yaml`

2. **Ошибка "Conflict: terminated by other getUpdates request"**:
   - Убедитесь, что запущен только один экземпляр бота: `ps aux | grep -e "--process-name=frontend"`
   - Завершите все найденные процессы: `pkill -f -- "--process-name=frontend"`
   - Подождите 5-10 минут и запустите снова

## Обновление приложения

### Обновление из репозитория

```bash
# Обновление до последней версии из репозитория
git pull

# Обновление зависимостей
conda env update -f environment.yml

# Перезапуск всех компонентов
pkill -f mongod
pkill -f -- "--process-name=backend"
pkill -f -- "--process-name=frontend"

./start_1_db.sh
./start_2_backend.sh
./start_3_frontend.sh
```

### Обновление структуры базы данных

Если в обновлении изменилась структура базы данных, может потребоваться миграция:

```bash
# Выполнение миграции данных
python scripts/migrate_data.py
```

## Заключение

Структурированный подход к развертыванию и обслуживанию приложения обеспечивает надежную и стабильную работу системы. Использование переменных окружения для настройки MongoDB и конфигурации Hydra для компонентов приложения позволяет гибко настраивать систему под различные условия эксплуатации.

При возникновении проблем или вопросов обращайтесь к документации в каталоге `docs/` или к разработчикам проекта.