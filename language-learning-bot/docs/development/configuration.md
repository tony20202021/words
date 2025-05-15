# Конфигурация с помощью Hydra

## Содержание
1. [Введение](#введение)
2. [Структура конфигурационных файлов](#структура-конфигурационных-файлов)
3. [Использование конфигурации в коде](#использование-конфигурации-в-коде)
4. [Примеры конфигурационных файлов](#примеры-конфигурационных-файлов)
5. [Переопределение конфигурации](#переопределение-конфигурации)
6. [Иерархия и композиция](#иерархия-и-композиция)
7. [Взаимодействие с переменными окружения](#взаимодействие-с-переменными-окружения)
8. [Рекомендации и лучшие практики](#рекомендации-и-лучшие-практики)

## Введение

Проект Language Learning Bot использует библиотеку Hydra для управления конфигурацией. Hydra предоставляет гибкий и модульный подход к управлению настройками приложения через YAML-файлы, позволяя разделить конфигурацию на логические группы и файлы.

Основные преимущества Hydra:
- Модульность - разделение конфигурации на логические компоненты
- Иерархическая структура - легкая организация сложных конфигураций
- Перегрузка параметров - возможность переопределять параметры из командной строки
- Композиция конфигураций - объединение нескольких конфигурационных файлов
- Удобство изменения параметров - все настройки хранятся в одном месте
- Типизация - параметры имеют конкретные типы данных
- Группировка - настройки группируются по функциональности

## Структура конфигурационных файлов

Конфигурация разделена на несколько файлов, расположенных в директориях:

### Фронтенд (frontend/conf/config/)

- **default.yaml** - основной файл, подключающий другие конфигурационные файлы
- **bot.yaml** - настройки Telegram-бота
- **api.yaml** - настройки для подключения к бэкенду
- **logging.yaml** - настройки логирования
- **learning.yaml** - настройки процесса обучения

### Бэкенд (backend/conf/config/)

- **default.yaml** - основной файл, подключающий другие конфигурационные файлы
- **api.yaml** - настройки API-сервера (хост, порт, CORS)
- **database.yaml** - настройки подключения к MongoDB
- **logging.yaml** - настройки логирования

## Использование конфигурации в коде

### Фронтенд (frontend/app/main.py)

```python
from hydra import compose, initialize
from omegaconf import OmegaConf

# Инициализация Hydra
initialize(config_path="../conf/config", version_base=None)
cfg = compose(config_name="default")

# Использование параметров из конфигурации
bot_token = cfg.bot.token
api_base_url = cfg.api.base_url
log_level = cfg.logging.level
max_interval = cfg.learning.max_interval
```

### Бэкенд (backend/app/main.py)

```python
from hydra import compose, initialize
from omegaconf import OmegaConf

# Инициализация Hydra
initialize(config_path="../conf/config", version_base=None)
cfg = compose(config_name="default")

# Использование параметров из конфигурации
api_host = cfg.api.host
api_port = cfg.api.port
db_url = cfg.database.mongodb.url
```

## Примеры конфигурационных файлов

### default.yaml (frontend)

```yaml
# Основная конфигурация приложения

# Подключение других конфигурационных файлов
defaults:
  - _self_
  - bot
  - api
  - logging
  - learning

# Настройки приложения
app:
  # Название приложения
  name: "Language Learning Bot"
  # Окружение (development, production)
  environment: "development"
  
# Настройки загрузки файлов
upload:
  # Директория для загруженных файлов
  folder: "./uploads"
  # Максимальный размер загружаемого файла в байтах
  max_size: 10485760  # 10MB
```

### bot.yaml

```yaml
# Конфигурация бота Telegram

# Токен для подключения к Telegram API
token: "YOUR_TELEGRAM_BOT_TOKEN"  # Замените на свой токен

# Настройки бота
skip_updates: true
polling_timeout: 30
retry_timeout: 5

# Настройки команд бота
commands:
  - command: "start"
    description: "Начать работу с ботом"
  - command: "help"
    description: "Получить справку"
  - command: "language"
    description: "Выбрать язык для изучения"
  - command: "study"
    description: "Начать изучение слов"
  - command: "settings"
    description: "Настройки процесса обучения"
  - command: "stats"
    description: "Показать статистику"
  - command: "hint"
    description: "Информация о подсказках"
  - command: "admin"
    description: "Режим администратора"

# Настройки для администраторов
admin:
  admin_ids: "1234567,7654321"  # Список ID администраторов
```

### api.yaml (frontend)

```yaml
# Конфигурация API-клиента
base_url: "http://localhost:8500"  # URL бэкенда
prefix: "/api"                     # Префикс API
timeout: 5                         # Таймаут запросов в секундах
retry_count: 3                     # Число повторных попыток
retry_delay: 1                     # Задержка между повторными попытками

# Пути API эндпоинтов
endpoints:
  # Эндпоинты для работы с языками
  languages:
    list: "/api/languages"
    get: "/api/languages/{id}"
    create: "/api/languages"
    update: "/api/languages/{id}"
    delete: "/api/languages/{id}"
  
  # Эндпоинты для работы со словами
  words:
    list: "/api/words"
    get: "/api/words/{id}"
    by_language: "/api/languages/{language_id}/words"
    create: "/api/words"
    update: "/api/words/{id}"
    delete: "/api/words/{id}"
    upload: "/api/words/upload"
  
  # Эндпоинты для работы с пользователями и статистикой
  users:
    list: "/api/users"
    get: "/api/users/{id}"
    create: "/api/users"
    update: "/api/users/{id}"
    delete: "/api/users/{id}"
    stats: "/api/users/{id}/stats"
    settings: "/api/users/{id}/settings"
```

### api.yaml (backend)

```yaml
# Конфигурация API-сервера
host: "0.0.0.0"  # Адрес для привязки сервера
port: 8500       # Порт для запуска API
prefix: "/api"   # Префикс для всех API-эндпоинтов
debug: true      # Режим отладки (true для development)

# Настройки CORS
cors_origins: "*"

# Настройки безопасности
secret_key: "your_secret_key_change_this_in_production"
jwt_algorithm: "HS256"
access_token_expire_minutes: 1440  # 24 hours
```

### database.yaml

```yaml
# Конфигурация базы данных
type: "mongodb"  # Тип базы данных

# Настройки MongoDB
mongodb:
  url: "mongodb://localhost:27017"  # URL подключения
  db_name: "language_learning_bot"  # Имя базы данных
  host: "localhost"                 # Хост MongoDB
  port: 27017                       # Порт MongoDB
  
  # Настройки пула соединений
  min_pool_size: 5
  max_pool_size: 10
  connection_timeout_ms: 5000
  
  # Настройки аутентификации (если необходимо)
  auth:
    enabled: false
    username: ""
    password: ""
    auth_source: "admin"
```

### logging.yaml

```yaml
# Конфигурация логирования

# Уровень логирования (DEBUG, INFO, WARNING, ERROR, CRITICAL)
level: "INFO"
# Формат сообщений лога
format: "%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s"
# Записывать ли логи в файл
log_to_file: true
# Путь к файлу лога
log_file: "logs/app.log"
# Директория для хранения файлов логов
log_dir: "logs"
# Максимальный размер файла лога перед ротацией (в байтах)
log_file_max_size: 5242880  # 5 MB
# Количество сохраняемых файлов лога при ротации
log_file_backup_count: 3
```

### learning.yaml

```yaml
# Конфигурация процесса обучения

# Настройки процесса обучения (значения по умолчанию)
# Стартовая позиция для слов (с какого номера начинать)
start_word: 1
# Флаг пропуска помеченных слов
skip_marked: false
# Флаг использования даты проверки
use_check_date: true
# Максимальный интервал для повторения (в днях)
max_interval: 32
# Коэффициент роста интервала при успешном запоминании
interval_multiplier: 2
# Интервал между проверками по умолчанию (в днях)
default_interval: 1
```

## Переопределение конфигурации

Hydra позволяет переопределять настройки из командной строки:

```bash
# Запуск с переопределением настроек
python app/main.py api.port=8501 logging.level=DEBUG
```

Также можно переопределять вложенные настройки:

```bash
# Переопределение вложенных настроек
python app/main.py database.mongodb.port=27018
```

## Иерархия и композиция

Hydra использует иерархическую структуру конфигурации, где конфигурационные файлы объединяются в единую конфигурацию:

```yaml
# default.yaml
defaults:
  - _self_
  - config1
  - config2
  - config3
```

В этом примере `default.yaml` загружается первым, затем последовательно загружаются и объединяются `config1.yaml`, `config2.yaml` и `config3.yaml`.

## Взаимодействие с переменными окружения

Hydra может использовать значения из переменных окружения:

```python
# Пример использования переменных окружения
db_url = cfg.database.mongodb.url if hasattr(cfg, "database") else os.getenv("MONGODB_URL", "mongodb://localhost:27017")
db_name = cfg.database.mongodb.db_name if hasattr(cfg, "database") else os.getenv("MONGODB_DB_NAME", "language_learning_bot")
```

Для экспорта переменных окружения из файла `.env` используется скрипт `run_export_env.sh`:

```bash
source ./run_export_env.sh
```

## Рекомендации и лучшие практики

### 1. Организация конфигурационных файлов

- Разбивайте конфигурацию на логические компоненты
- Используйте иерархию для организации сложных конфигураций
- Храните связанные настройки в одном файле

### 2. Обработка конфиденциальных данных

- Не включайте токены и пароли в исходный код
- Используйте переменные окружения для конфиденциальных данных
- Создайте шаблонные файлы (например, `bot.yaml.example`) без реальных значений
- Настройте права доступа к файлам конфигурации, содержащим секретные данные

### 3. Значения по умолчанию

- Всегда указывайте разумные значения по умолчанию
- Проверяйте наличие обязательных параметров в коде
- Документируйте назначение каждого параметра

### 4. Версионирование конфигурации

- Включайте пример конфигурационных файлов в систему контроля версий
- Исключайте файлы с реальными значениями из системы контроля версий
- Документируйте изменения в конфигурации при обновлении версии приложения

### 5. Рабочий процесс разработки

- Используйте разные конфигурации для разработки и продакшена
- Переопределяйте минимальное количество параметров при запуске
- Проверяйте конфигурацию перед деплоем

### 6. Отладка конфигурации

Для отладки конфигурации можно использовать функцию `OmegaConf.to_yaml()`:

```python
from omegaconf import OmegaConf

# Вывод конфигурации в YAML-формате
print(OmegaConf.to_yaml(cfg))
```

Это позволяет увидеть всю конфигурацию после объединения всех файлов и переопределений.

### 4.3. Обновление configuration.md

Добавить пример конфигурации для распознавания речи:

```markdown
### Пример конфигурации распознавания речи

```yaml
# Конфигурация распознавания речи
voice_recognition:
  # Размер модели Whisper (tiny, base, small, medium, large)
  # - tiny: наименьший размер, самая быстрая, менее точная (~150MB)
  # - base: базовая модель (~300MB)
  # - small: сбалансированная модель (~500MB), рекомендуется
  # - medium: средняя модель (~1.5GB)
  # - large: большая модель (~3GB), самая точная, но самая медленная
  model_size: "small"
  
  # Язык распознавания
  language: "ru"
  
  # Директория для временных аудиофайлов
  temp_dir: "temp"
  
  # Максимальная длительность голосового сообщения в секундах
  max_duration: 60
  
  # Настройки для локального GPU (если доступен)
  use_gpu: true
  
  # Включение/отключение распознавания речи
  enabled: true

## 5. Обновление каталогов проекта

Необходимо создать директорию для временных аудиофайлов:

```bash
mkdir -p frontend/temp
И добавить её в .gitignore:
# Временные аудиофайлы
frontend/temp/