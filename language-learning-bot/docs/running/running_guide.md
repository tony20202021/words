# Руководство по запуску Language Learning Bot

## Содержание
1. [Общая информация](#общая-информация)
2. [Последовательность запуска](#последовательность-запуска)
3. [Запуск MongoDB](#запуск-mongodb)
4. [Запуск бэкенда](#запуск-бэкенда)
5. [Запуск Writing Service](#запуск-writing-service)
6. [Запуск фронтенда](#запуск-фронтенда)
7. [Режим автоматического перезапуска](#режим-автоматического-перезапуска)
8. [Управление запущенными процессами](#управление-запущенными-процессами)
9. [Мониторинг логов](#мониторинг-логов)
10. [Проверка работоспособности](#проверка-работоспособности)
11. [Устранение проблем](#устранение-проблем)

## Общая информация

Language Learning Bot состоит из четырех основных компонентов, которые необходимо запускать в определенной последовательности:

1. **MongoDB** - база данных для хранения информации о языках, словах и пользователях
2. **Бэкенд (REST API)** - сервер, обрабатывающий запросы и взаимодействующий с базой данных (порт 8500)
3. **Writing Service** - микросервис генерации картинок написания (порт 8600)
4. **Фронтенд (Telegram-бот)** - интерфейс взаимодействия с пользователем через Telegram

Для правильной работы всех компонентов требуется:
- Python 3.8+
- MongoDB 5.0+
- Telegram Bot API ключ (токен)

## Последовательность запуска

Для корректной работы приложения необходимо запускать компоненты в следующем порядке:

1. MongoDB (база данных)
2. Бэкенд (REST API)
3. Writing Service (генерация картинок)
4. Фронтенд (Telegram-бот)

Ниже будет подробно рассмотрен процесс запуска каждого компонента.

## Запуск MongoDB

### Использование скрипта start_1_db.sh

Рекомендуемый способ запуска MongoDB:

```bash
# Сделать скрипт исполняемым (если еще не сделано)
chmod +x start_1_db.sh

# Запустить MongoDB
./start_1_db.sh
```

Скрипт автоматически:
- Загружает настройки из файла `.env`
- Проверяет, запущен ли уже экземпляр MongoDB
- Создает необходимые директории при их отсутствии
- Запускает MongoDB в фоновом режиме

### Ручной запуск MongoDB

Альтернативный способ запуска MongoDB:

```bash
# Запуск с конфигурационным файлом
~/mongodb/bin/mongod --config ~/mongodb/config/mongod.conf --fork

# Проверка запуска
ps aux | grep mongod
```

## Запуск бэкенда

### Использование скрипта start_2_backend.sh

Рекомендуемый способ запуска бэкенда:

```bash
# Сделать скрипт исполняемым (если еще не сделано)
chmod +x start_2_backend.sh

# Запустить бэкенд
./start_2_backend.sh
```

Скрипт автоматически:
- Проверяет, запущен ли уже бэкенд
- Завершает конфликтующие процессы
- Запускает Python-модуль с нужными параметрами
- Сохраняет PID процесса для последующего управления

### Запуск бэкенда на альтернативном порту

Если порт по умолчанию (8500) занят, вы можете указать другой порт:

```bash
# С использованием переменной окружения
PORT=8501 ./start_2_backend.sh

# Или напрямую через параметр
./start_2_backend.sh --port=8501
```

## Запуск Writing Service

### 🆕 Использование скрипта start_4_writing_service.sh

**Writing Service** - новый микросервис для генерации картинок написания:

```bash
# Сделать скрипт исполняемым (если еще не сделано)
chmod +x start_4_writing_service.sh

# Запустить Writing Service
./start_4_writing_service.sh
```

Скрипт автоматически:
- Проверяет, запущен ли уже Writing Service
- Завершает конфликтующие процессы на порту 8600
- Запускает микросервис с параметром `--process-name=writing_service`
- Сохраняет PID процесса в файл `.writing_service.pid`

### Запуск Writing Service на альтернативном порту

```bash
# С указанием альтернативного порта
./start_4_writing_service.sh --port=8601

# С использованием переменной окружения
WRITING_SERVICE_PORT=8601 ./start_4_writing_service.sh
```

### Проверка Writing Service

После запуска проверьте работоспособность сервиса:

```bash
# Базовая проверка здоровья
curl http://localhost:8600/health

# Проверка API статуса
curl http://localhost:8600/api/writing/status

# Открыть документацию API в браузере
open http://localhost:8600/api/docs  # macOS
# или
xdg-open http://localhost:8600/api/docs  # Linux
```

### Ручной запуск Writing Service

Альтернативный способ запуска Writing Service:

```bash
# Активация окружения (если используется Conda)
conda activate language-learning-bot

# Запуск Writing Service
cd writing_service
python -m app.main_writing_service --process-name=writing_service --port=8600
```

## Запуск фронтенда

### Использование скрипта start_3_frontend.sh

Рекомендуемый способ запуска фронтенда:

```bash
# Сделать скрипт исполняемым (если еще не сделано)
chmod +x start_3_frontend.sh

# Запустить фронтенд
./start_3_frontend.sh
```

Скрипт автоматически:
- Проверяет, запущен ли уже фронтенд
- Завершает конфликтующие процессы
- Запускает Python-модуль с нужными параметрами
- Сохраняет PID процесса для последующего управления

### Ручной запуск фронтенда

Альтернативный способ запуска фронтенда:

```bash
# Активация окружения (если используется Conda)
conda activate language-learning-bot

# Запуск фронтенда
cd frontend
python -m app.main_frontend --process-name=frontend
```

## Режим автоматического перезапуска

Режим автоматического перезапуска полезен при разработке для быстрого применения изменений кода.

### Установка необходимых зависимостей

```bash
# Сделать скрипт исполняемым
chmod +x setup_watchdog.sh

# Установить зависимости для автоперезапуска
./setup_watchdog.sh
```

### Запуск фронтенда с автоперезапуском

```bash
# Сделать скрипт исполняемым
chmod +x start_3_frontend_auto_reload.sh

# Запустить фронтенд в режиме автоперезапуска
./start_3_frontend_auto_reload.sh
```

Фронтенд будет автоматически перезапускаться при изменении файлов в директориях:
- `frontend/app/`
- `frontend/conf/config/`

## Управление запущенными процессами

### Проверка запущенных процессов

```bash
# Показать PID всех сервисов из файлов
cat .backend.pid
cat .writing_service.pid  # 🆕 Новый сервис
cat .frontend.pid

# Проверка процессов по PID
ps -p $(cat .backend.pid)
ps -p $(cat .writing_service.pid)  # 🆕
ps -p $(cat .frontend.pid)

# Поиск процессов по идентификатору
ps aux | grep -e "--process-name=frontend"
ps aux | grep -e "--process-name=backend"
ps aux | grep -e "--process-name=writing_service"  # 🆕
ps aux | grep mongod
```

### Завершение процессов

```bash
# Корректное завершение всех сервисов
kill $(cat .backend.pid)
kill $(cat .writing_service.pid)  # 🆕
kill $(cat .frontend.pid)

# Принудительное завершение в случае зависания
kill -9 $(cat .backend.pid)
kill -9 $(cat .writing_service.pid)  # 🆕
kill -9 $(cat .frontend.pid)

# Завершение по идентификатору процесса
pkill -f -- "--process-name=frontend"
pkill -f -- "--process-name=backend"
pkill -f -- "--process-name=writing_service"  # 🆕
pkill -f mongod
```

## Мониторинг логов

### Просмотр логов всех компонентов

```bash
# Просмотр логов MongoDB
tail -f ~/mongodb/log/mongod.log

# Просмотр логов бэкенда
tail -f backend/logs/backend.log

# Просмотр логов Writing Service (🆕)
tail -f writing_service/logs/writing_service.log

# Просмотр логов фронтенда
tail -f frontend/logs/app.log
```

### Просмотр всех логов одновременно

```bash
# Использование multitail (требуется установка)
multitail ~/mongodb/log/mongod.log \
          backend/logs/backend.log \
          writing_service/logs/writing_service.log \
          frontend/logs/app.log
```

## Проверка работоспособности

### Проверка бэкенда

```bash
# Проверка доступности API
curl http://localhost:8573/api/health

# Проверка списка языков
curl http://localhost:8573/api/languages
```

### 🆕 Проверка Writing Service

```bash
# Проверка базового health check
curl http://localhost:8600/health

# Проверка детального health check
curl http://localhost:8600/health/detailed

# Проверка API статуса
curl http://localhost:8600/api/writing/status

# Тестирование генерации изображения
curl -X POST http://localhost:8600/api/writing/generate-writing-image \
  -H "Content-Type: application/json" \
  -d '{"word": "test", "language": "english", "style": "print"}'
```

### Проверка фронтенда

1. Откройте Telegram
2. Найдите вашего бота по имени или ссылке
3. Отправьте команду `/start`
4. Проверьте отправку и получение сообщений

### Мониторинг ресурсов

```bash
# Просмотр использования CPU и памяти
ps -o pid,cmd,%cpu,%mem -p \
  $(pgrep -f mongod) \
  $(pgrep -f -- "--process-name=backend") \
  $(pgrep -f -- "--process-name=writing_service") \
  $(pgrep -f -- "--process-name=frontend")

# Мониторинг в реальном времени
top -p $(pgrep -f mongod),$(pgrep -f -- "--process-name=backend"),$(pgrep -f -- "--process-name=writing_service"),$(pgrep -f -- "--process-name=frontend")
```

## Устранение проблем

### Writing Service не запускается

**Симптомы**: Ошибки при запуске Writing Service, скрипт `start_4_writing_service.sh` завершается с ошибкой.

**Решения**:
1. Проверьте логи Writing Service:
   ```bash
   cat writing_service/logs/writing_service.log
   ```

2. Проверьте, не занят ли порт Writing Service:
   ```bash
   lsof -i :8600
   ```

3. Проверьте переменные окружения:
   ```bash
   source ./run_export_env.sh
   echo $WRITING_SERVICE_HOST
   echo $WRITING_SERVICE_PORT
   ```

4. Проверьте права доступа к директориям:
   ```bash
   ls -la writing_service/logs/
   ls -la writing_service/temp/
   ```

5. Если порт занят, завершите процесс:
   ```bash
   pkill -f -- "--process-name=writing_service"
   # или используйте другой порт
   ./start_4_writing_service.sh --port=8601
   ```

### Интеграция между сервисами не работает

**Симптомы**: Фронтенд не может получить изображения от Writing Service.

**Решения**:
1. Проверьте доступность Writing Service:
   ```bash
   curl http://localhost:8600/health
   ```

2. Проверьте сетевое взаимодействие:
   ```bash
   # Из фронтенда должно быть доступно:
   curl http://localhost:8600/api/writing/status
   ```

3. Проверьте конфигурацию в фронтенде:
   ```bash
   # Убедитесь, что Writing Service URL правильно настроен
   grep -r "8600" frontend/conf/config/
   ```

### Полный перезапуск системы

Если возникли серьезные проблемы, выполните полный перезапуск:

```bash
# Остановка всех процессов
pkill -f mongod
pkill -f -- "--process-name=backend"
pkill -f -- "--process-name=writing_service"  # 🆕
pkill -f -- "--process-name=frontend"

# Очистка PID файлов
rm -f .backend.pid .writing_service.pid .frontend.pid

# Ожидание завершения процессов
sleep 5

# Запуск всех компонентов
./start_1_db.sh
./start_2_backend.sh
./start_4_writing_service.sh  # 🆕
./start_3_frontend.sh

# Проверка запуска всех сервисов
curl http://localhost:8573/api/health
curl http://localhost:8600/health
```

## Быстрый старт для новых разработчиков

```bash
# 1. Настройка окружения
conda env create -f environment.yml
conda activate language-learning-bot
cp .env.example .env
# Отредактируйте .env файл

# 2. Экспорт переменных
source ./run_export_env.sh

# 3. Инициализация базы данных
./start_1_db.sh
python scripts/init_db.py
python scripts/seed_data.py  # опционально

# 4. Запуск всех сервисов
./start_2_backend.sh
./start_3_frontend.sh
./start_4_writing_service.sh  # 🆕 Новый сервис

# 5. Проверка работоспособности
curl http://localhost:8573/api/health  # Backend
curl http://localhost:8600/health      # Writing Service
# Отправьте /start боту в Telegram
```
