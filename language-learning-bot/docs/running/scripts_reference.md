# Руководство по управлению скриптами в Language Learning Bot

## Содержание
1. [Обзор скриптов](#обзор-скриптов)
2. [Скрипты запуска компонентов](#скрипты-запуска-компонентов)
    - [start_1_db.sh](#start_1_dbsh)
    - [start_2_backend.sh](#start_2_backendsh)
    - [start_3_frontend.sh](#start_3_frontendsh)
    - [start_3_frontend_auto_reload.sh](#start_3_frontend_auto_reloadsh)
3. [Скрипты управления окружением](#скрипты-управления-окружением)
    - [run_export_env.sh](#run_export_envsh)
    - [setup_watchdog.sh](#setup_watchdogsh)
4. [Скрипты тестирования](#скрипты-тестирования)
    - [run_tests.sh](#run_testssh)
5. [Скрипты инициализации и обслуживания БД](#скрипты-инициализации-и-обслуживания-бд)
    - [init_db.py](#init_dbpy)
    - [seed_data.py](#seed_datapy)
    - [migrate_data.py](#migrate_datapy)
    - [create_user_language_settings_collection.py](#create_user_language_settings_collectionpy)
6. [Скрипты администрирования](#скрипты-администрирования)
    - [admin_manager.py](#admin_managerpy)
7. [Дополнительные скрипты](#дополнительные-скрипты)
    - [watch_and_reload.py](#watch_and_reloadpy)
8. [Типичные сценарии использования](#типичные-сценарии-использования)
9. [Устранение проблем](#устранение-проблем)

## Обзор скриптов

Проект Language Learning Bot использует набор скриптов для управления различными аспектами работы приложения:
- Скрипты запуска компонентов (MongoDB, бэкенд, фронтенд)
- Скрипты управления окружением
- Скрипты тестирования
- Скрипты инициализации и обслуживания базы данных
- Скрипты администрирования

Эти скрипты облегчают разработку, тестирование и обслуживание приложения.

## Скрипты запуска компонентов

### start_1_db.sh

**Назначение**: Запуск MongoDB

**Основные операции**:
- Загрузка настроек из файла `.env`
- Проверка, запущен ли уже MongoDB
- Создание необходимых директорий
- Генерация/обновление конфигурационного файла
- Запуск MongoDB в фоновом режиме

**Использование**:
```bash
chmod +x start_1_db.sh
./start_1_db.sh
```

**Результаты работы**:
- Запущенный сервер MongoDB
- Сообщение о статусе запуска

---

### start_2_backend.sh

**Назначение**: Запуск бэкенд-сервиса (REST API)

**Основные операции**:
- Проверка, запущен ли уже процесс бэкенда
- Проверка занятости порта
- Запуск Python-модуля с параметром `--process-name=backend`
- Сохранение PID процесса в файл `.backend.pid`

**Использование**:
```bash
chmod +x start_2_backend.sh
./start_2_backend.sh [--port=PORT]
```

**Параметры**:
- `--port=PORT` - Опциональный параметр для указания альтернативного порта

**Результаты работы**:
- Запущенный бэкенд-сервер
- Сообщение о статусе запуска
- Файл `.backend.pid` с идентификатором процесса

---

### start_3_frontend.sh

**Назначение**: Запуск фронтенд-сервиса (Telegram-бот)

**Основные операции**:
- Проверка, запущен ли уже процесс фронтенда
- Завершение конфликтующих процессов
- Запуск Python-модуля с параметром `--process-name=frontend`
- Сохранение PID процесса в файл `.frontend.pid`

**Использование**:
```bash
chmod +x start_3_frontend.sh
./start_3_frontend.sh
```

**Результаты работы**:
- Запущенный Telegram-бот
- Сообщение о статусе запуска
- Файл `.frontend.pid` с идентификатором процесса

---

### start_3_frontend_auto_reload.sh

**Назначение**: Запуск фронтенда с автоматическим перезапуском при изменении файлов

**Основные операции**:
- Запуск скрипта `watch_and_reload.py` для мониторинга изменений
- Настройка параметров мониторинга (пути, расширения, игнорируемые директории)
- Автоматический перезапуск при изменениях

**Использование**:
```bash
chmod +x start_3_frontend_auto_reload.sh
./start_3_frontend_auto_reload.sh
```

**Результаты работы**:
- Запущенный Telegram-бот с автоперезапуском
- Активный мониторинг изменений файлов

## Скрипты управления окружением

### run_export_env.sh

**Назначение**: Экспорт переменных окружения из файла `.env`

**Основные операции**:
- Проверка наличия файла `.env`
- Загрузка переменных из файла в текущее окружение
- Установка значений по умолчанию для отсутствующих переменных

**Использование**:
```bash
source ./run_export_env.sh
```

**Важно**: Используйте команду `source` вместо простого запуска, чтобы переменные экспортировались в текущую сессию.

**Результаты работы**:
- Экспортированные переменные окружения
- Вывод статуса загрузки

---

### setup_watchdog.sh

**Назначение**: Установка зависимостей для автоматического перезапуска

**Основные операции**:
- Проверка наличия pip
- Установка библиотеки watchdog, если она не установлена
- Проверка наличия других необходимых зависимостей

**Использование**:
```bash
chmod +x setup_watchdog.sh
./setup_watchdog.sh
```

**Результаты работы**:
- Установленная библиотека watchdog
- Сообщение о статусе установки

## Скрипты тестирования

### run_tests.sh

**Назначение**: Запуск тестов проекта

**Основные операции**:
- Проверка аргументов командной строки
- Запуск тестов с помощью pytest
- Формирование отчета о покрытии кода (при указании параметра)

**Использование**:
```bash
chmod +x run_tests.sh
./run_tests.sh [параметры]
```

**Параметры**:
- `--component frontend` - Запуск только тестов фронтенда
- `--component backend` - Запуск только тестов бэкенда
- `--verbose` - Подробный вывод тестов
- `--coverage` - Генерация отчета о покрытии кода
- `--html` - Генерация HTML-отчета о покрытии (работает с `--coverage`)
- `--specific PATH` - Запуск конкретного теста или модуля

**Результаты работы**:
- Результаты выполнения тестов
- Отчеты о покрытии кода (при указании соответствующих параметров)

## Скрипты инициализации и обслуживания БД

### init_db.py

**Назначение**: Инициализация базы данных

**Основные операции**:
- Создание необходимых коллекций
- Создание индексов
- Настройка схемы базы данных

**Использование**:
```bash
python scripts/init_db.py
```

**Результаты работы**:
- Инициализированная база данных
- Сообщения о создании коллекций и индексов

---

### seed_data.py

**Назначение**: Заполнение базы данных тестовыми данными

**Основные операции**:
- Добавление тестовых языков
- Добавление тестовых слов
- Создание тестовых пользователей

**Использование**:
```bash
python scripts/seed_data.py
```

**Результаты работы**:
- Заполненная тестовыми данными база данных
- Сообщения о добавленных объектах

---

### migrate_data.py

**Назначение**: Миграция данных при изменении структуры базы данных

**Основные операции**:
- Обновление схемы базы данных при изменениях
- Преобразование существующих данных для соответствия новой схеме
- Сохранение целостности данных

**Использование**:
```bash
python scripts/migrate_data.py
```

**Результаты работы**:
- Обновленная структура базы данных
- Сообщения о миграции

---

### create_user_language_settings_collection.py

**Назначение**: Создание коллекции для хранения настроек пользователей по языкам

**Основные операции**:
- Создание коллекции `user_language_settings`
- Добавление составного уникального индекса по полям `user_id` и `language_id`

**Использование**:
```bash
python scripts/create_user_language_settings_collection.py
```

**Результаты работы**:
- Созданная коллекция `user_language_settings`
- Настроенные индексы
- Сообщение о статусе операции

## Скрипты администрирования

### admin_manager.py

**Назначение**: Управление пользователями и администраторами через API

**Основные операции**:
- Получение списка пользователей
- Поиск пользователя по Telegram ID
- Просмотр детальной информации о пользователе
- Назначение пользователя администратором

**Использование**:
```bash
# Вывод списка пользователей
python scripts/admin_manager.py list [--limit N]

# Поиск пользователя по Telegram ID
python scripts/admin_manager.py find TELEGRAM_ID

# Просмотр подробной информации о пользователе
python scripts/admin_manager.py info TELEGRAM_ID

# Назначение пользователя администратором
python scripts/admin_manager.py make-admin USER_ID

# Интерактивное назначение администратора
python scripts/admin_manager.py promote TELEGRAM_ID
```

**Параметры для команды list**:
- `--limit N` - Ограничение количества выводимых пользователей (по умолчанию: 100)

**Результаты работы**:
- Информация о пользователях
- Статус операций с пользователями
- Сообщения об ошибках (при наличии)

## Дополнительные скрипты

### watch_and_reload.py

**Назначение**: Мониторинг изменений файлов и автоматический перезапуск фронтенда

**Основные операции**:
- Отслеживание изменений в указанных директориях
- Фильтрация по расширениям файлов
- Игнорирование указанных директорий
- Автоматический перезапуск процесса при изменениях

**Использование**:
```bash
python frontend/watch_and_reload.py \
    --script PATH_TO_SCRIPT \
    --paths PATH1 PATH2 \
    --extensions EXT1 EXT2 \
    --ignore-dirs DIR1 DIR2
```

**Параметры**:
- `--script` - Путь к основному скрипту для запуска (по умолчанию: `app/main_frontend.py`)
- `--paths` - Список директорий для мониторинга (по умолчанию: `['app']`)
- `--extensions` - Расширения файлов для отслеживания (по умолчанию: `['.py', '.yaml', '.yml']`)
- `--ignore-dirs` - Директории для игнорирования (по умолчанию: `['__pycache__', '.git', 'env', 'venv', 'logs']`)
- `--process-name` - Имя процесса для идентификации (по умолчанию: `frontend_autoreload`)

**Результаты работы**:
- Запущенный процесс мониторинга
- Сообщения об обнаруженных изменениях
- Автоматически перезапускаемый процесс фронтенда

## Типичные сценарии использования

### Первоначальная настройка проекта

```bash
# Клонирование репозитория
git clone https://github.com/username/language-learning-bot.git
cd language-learning-bot

# Создание и активация окружения
conda env create -f environment.yml
conda activate language-learning-bot

# Копирование примера конфигурации
cp .env.example .env

# Редактирование .env файла (добавление токена бота и т.д.)
nano .env

# Экспорт переменных окружения
source ./run_export_env.sh

# Запуск MongoDB
./start_1_db.sh

# Инициализация базы данных
python scripts/init_db.py

# Заполнение тестовыми данными (опционально)
python scripts/seed_data.py

# Запуск бэкенда
./start_2_backend.sh

# Запуск фронтенда
./start_3_frontend.sh
```

### Разработка с автоперезагрузкой

```bash
# Установка необходимых зависимостей
./setup_watchdog.sh

# Запуск MongoDB и бэкенда
./start_1_db.sh
./start_2_backend.sh

# Запуск фронтенда с автоперезагрузкой
./start_3_frontend_auto_reload.sh
```

### Тестирование изменений

```bash
# Запуск всех тестов
./run_tests.sh

# Запуск только тестов фронтенда
./run_tests.sh --component frontend

# Запуск с отчетом о покрытии кода
./run_tests.sh --coverage --html
```

### Административные операции

```bash
# Назначение пользователя администратором
python scripts/admin_manager.py find 123456789
python scripts/admin_manager.py make-admin user_id_123
```

### Перезапуск всех компонентов

```bash
# Остановка процессов
pkill -f mongod
pkill -f -- "--process-name=backend"
pkill -f -- "--process-name=frontend"

# Запуск процессов
./start_1_db.sh
./start_2_backend.sh
./start_3_frontend.sh
```

## Устранение проблем

### MongoDB не запускается

**Симптомы**: Ошибки при запуске MongoDB, скрипт `start_1_db.sh` завершается с ошибкой.

**Решения**:
1. Проверьте логи MongoDB:
   ```bash
   cat ~/mongodb/log/mongod.log
   ```

2. Проверьте наличие директорий для данных и логов:
   ```bash
   ls -la ~/mongodb/data
   ls -la ~/mongodb/log
   ```

3. Проверьте права доступа к директориям:
   ```bash
   chmod 755 ~/mongodb/data
   chmod 755 ~/mongodb/log
   ```

4. Проверьте, не занят ли порт MongoDB:
   ```bash
   lsof -i :27017
   ```

5. Если порт занят, завершите процесс:
   ```bash
   pkill -f mongod
   ```

### Бэкенд не запускается

**Симптомы**: Ошибки при запуске бэкенда, скрипт `start_2_backend.sh` завершается с ошибкой.

**Решения**:
1. Проверьте логи бэкенда:
   ```bash
   cat backend/logs/backend.log
   ```

2. Проверьте, не занят ли порт бэкенда:
   ```bash
   lsof -i :8500
   ```

3. Проверьте переменные окружения:
   ```bash
   source ./run_export_env.sh
   echo $MONGODB_HOST
   echo $MONGODB_PORT
   echo $MONGODB_DB_NAME
   ```

4. Проверьте подключение к MongoDB:
   ```bash
   mongo --eval "db.stats()"
   ```

5. Если порт занят, попробуйте использовать другой порт:
   ```bash
   ./start_2_backend.sh --port=8501
   ```

### Фронтенд не запускается

**Симптомы**: Ошибки при запуске фронтенда, скрипт `start_3_frontend.sh` завершается с ошибкой.

**Решения**:
1. Проверьте логи фронтенда:
   ```bash
   cat frontend/logs/app.log
   ```

2. Проверьте, запущен ли бэкенд:
   ```bash
   ps -p $(cat .backend.pid)
   ```

3. Проверьте доступность API бэкенда:
   ```bash
   curl http://localhost:8500/api/health
   ```

4. Проверьте переменную окружения с токеном бота:
   ```bash
   source ./run_export_env.sh
   echo $TELEGRAM_BOT_TOKEN
   ```

5. Завершите все конфликтующие процессы и попробуйте снова:
   ```bash
   pkill -f -- "--process-name=frontend"
   ./start_3_frontend.sh
   ```

### Автоперезапуск не работает

**Симптомы**: Изменения в файлах не приводят к автоматическому перезапуску.

**Решения**:
1. Проверьте, установлена ли библиотека watchdog:
   ```bash
   ./setup_watchdog.sh
   ```

2. Проверьте, что изменяемые файлы находятся в отслеживаемых директориях:
   ```bash
   cat start_3_frontend_auto_reload.sh
   ```

3. Проверьте наличие нескольких экземпляров процесса:
   ```bash
   ps aux | grep watch_and_reload
   ```

4. Убедитесь, что расширение изменяемого файла входит в список отслеживаемых:
   ```bash
   cat start_3_frontend_auto_reload.sh | grep extensions
   ```

5. Увеличьте интервал троттлинга:
   ```bash
   python frontend/watch_and_reload.py --throttle-interval 5 ... [другие параметры]
   ```

### Конфликты процессов

**Симптомы**: Ошибки при запуске, сообщения о занятости портов.

**Решения**:
1. Поиск всех процессов и их PID:
   ```bash
   ps aux | grep -e "mongod" -e "--process-name=backend" -e "--process-name=frontend"
   ```

2. Завершение всех процессов:
   ```bash
   pkill -f mongod
   pkill -f -- "--process-name=backend"
   pkill -f -- "--process-name=frontend"
   pkill -f -- "--process-name=frontend_autoreload"
   ```

3. Удаление PID-файлов:
   ```bash
   rm -f .backend.pid .frontend.pid
   ```

4. Перезапуск компонентов:
   ```bash
   ./start_1_db.sh
   ./start_2_backend.sh
   ./start_3_frontend.sh
   ```