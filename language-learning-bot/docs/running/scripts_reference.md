# Руководство по управлению скриптами в Language Learning Bot

## Содержание
1. [Обзор скриптов](#обзор-скриптов)
2. [Скрипты запуска компонентов](#скрипты-запуска-компонентов)
    - [start_1_db.sh](#start_1_dbsh)
    - [start_2_backend.sh](#start_2_backendsh)
    - [start_3_frontend.sh](#start_3_frontendsh)
    - [start_4_writing_images_service.sh](#start_4_writing_images_servicesh)
    - [start_3_frontend_auto_reload.sh](#start_3_frontend_auto_reloadsh)
3. [Скрипты управления окружением](#скрипты-управления-окружением)
    - [run_export_env.sh](#run_export_envsh)
    - [setup_watchdog.sh](#setup_watchdogsh)
4. [Скрипты тестирования](#скрипты-тестирования)
    - [run_tests.sh](#run_testssh)
5. [Скрипты инициализации и обслуживания БД](#скрипты-инициализации-и-обслуживания-бд)
6. [Скрипты администрирования](#скрипты-администрирования)
7. [Дополнительные скрипты](#дополнительные-скрипты)
8. [Типичные сценарии использования](#типичные-сценарии-использования)
9. [Устранение проблем](#устранение-проблем)

## Обзор скриптов

Проект Language Learning Bot использует набор скриптов для управления четырьмя основными компонентами:
- **MongoDB** - база данных
- **Backend API** - основной сервер (порт 8500)
- **Frontend** - Telegram-бот
- **Writing Service** - микросервис генерации картинок (порт 8600)

Дополнительно предоставляются скрипты для тестирования, управления окружением и администрирования.

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
- Запущенный сервер MongoDB на порту 27017
- Сообщение о статусе запуска

---

### start_2_backend.sh

**Назначение**: Запуск бэкенд-сервиса (REST API)

**Основные операции**:
- Проверка, запущен ли уже процесс бэкенда
- Проверка занятости порта 8500
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
- Запущенный бэкенд-сервер на порту 8500
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

### start_4_writing_images_service.sh

**🆕 Назначение**: Запуск Writing Service (микросервис генерации картинок)

**Основные операции**:
- Проверка, запущен ли уже процесс Writing Service
- Проверка занятости порта 8600
- Запуск Python-модуля с параметром `--process-name=writing_images_service`
- Сохранение PID процесса в файл `.writing_images_service.pid`

**Использование**:
```bash
chmod +x start_4_writing_images_service.sh
./start_4_writing_images_service.sh [--port=PORT]
```

**Параметры**:
- `--port=PORT` - Опциональный параметр для указания альтернативного порта (по умолчанию: 8600)

**Результаты работы**:
- Запущенный Writing Service на порту 8600
- API доступен по адресу `http://localhost:8600/api`
- Swagger документация: `http://localhost:8600/api/docs`
- Файл `.writing_images_service.pid` с идентификатором процесса

**Проверка работоспособности**:
```bash
# Проверка health check
curl http://localhost:8600/health

# Проверка API статуса
curl http://localhost:8600/api/writing/status
```

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

**Использование**:
```bash
source ./run_export_env.sh
```

**Важно**: Используйте команду `source` вместо простого запуска, чтобы переменные экспортировались в текущую сессию.

---

### setup_watchdog.sh

**Назначение**: Установка зависимостей для автоматического перезапуска

**Использование**:
```bash
chmod +x setup_watchdog.sh
./setup_watchdog.sh
```

## Скрипты тестирования

### run_tests.sh

**🆕 Назначение**: Запуск тестов проекта с поддержкой всех компонентов

**Основные операции**:
- Проверка аргументов командной строки
- Запуск тестов с помощью pytest для выбранных компонентов
- Формирование отчета о покрытии кода (при указании параметра)

**Использование**:
```bash
chmod +x run_tests.sh
./run_tests.sh [параметры]
```

**Параметры**:
- `--component frontend` - Запуск только тестов фронтенда
- `--component backend` - Запуск только тестов бэкенда
- `--component common` - Запуск только тестов общих модулей
- `--component writing_images_service` - 🆕 Запуск только тестов Writing Service
- `--component all` - Запуск всех тестов (по умолчанию)
- `--verbose` - Подробный вывод тестов
- `--coverage` - Генерация отчета о покрытии кода
- `--html` - Генерация HTML-отчета о покрытии (работает с `--coverage`)
- `--specific PATH` - Запуск конкретного теста или модуля

**Примеры использования**:
```bash
# Запуск всех тестов
./run_tests.sh

# Запуск только тестов Writing Service
./run_tests.sh --component writing_images_service

# Запуск с отчетом о покрытии
./run_tests.sh --coverage --html

# Запуск конкретного теста
./run_tests.sh --specific writing_images_service/tests/test_health.py
```

**Результаты работы**:
- Результаты выполнения тестов для каждого компонента
- Отчеты о покрытии кода (при указании соответствующих параметров)
- Сводка по всем компонентам

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

# Запуск всех компонентов
./start_1_db.sh
./start_2_backend.sh
./start_4_writing_images_service.sh  # 🆕 Новый сервис
./start_3_frontend.sh
```

### Разработка с автоперезагрузкой

```bash
# Установка необходимых зависимостей
./setup_watchdog.sh

# Запуск базовых сервисов
./start_1_db.sh
./start_2_backend.sh
./start_4_writing_images_service.sh

# Запуск фронтенда с автоперезагрузкой
./start_3_frontend_auto_reload.sh
```

### Полное тестирование системы

```bash
# Запуск всех тестов
./run_tests.sh

# Запуск тестов по компонентам
./run_tests.sh --component frontend
./run_tests.sh --component backend
./run_tests.sh --component writing_images_service  # 🆕
./run_tests.sh --component common

# Генерация отчетов о покрытии
./run_tests.sh --coverage --html
```

### Проверка состояния сервисов

```bash
# Проверка процессов
ps aux | grep -e "mongod" -e "--process-name=backend" -e "--process-name=frontend" -e "--process-name=writing_images_service"

# Проверка портов
lsof -i :27017  # MongoDB
lsof -i :8500   # Backend
lsof -i :8600   # Writing Service

# Проверка API
curl http://localhost:8500/api/health      # Backend health
curl http://localhost:8600/health          # Writing Service health
curl http://localhost:8600/api/docs        # Writing Service docs
```

### Перезапуск всех компонентов

```bash
# Остановка процессов
pkill -f mongod
pkill -f -- "--process-name=backend"
pkill -f -- "--process-name=frontend"
pkill -f -- "--process-name=writing_images_service"  # 🆕

# Очистка PID файлов
rm -f .backend.pid .frontend.pid .writing_images_service.pid

# Запуск процессов
./start_1_db.sh
./start_2_backend.sh
./start_4_writing_images_service.sh  # 🆕
./start_3_frontend.sh
```

## Устранение проблем

### Writing Service не запускается

**Симптомы**: Ошибки при запуске Writing Service, скрипт `start_4_writing_images_service.sh` завершается с ошибкой.
