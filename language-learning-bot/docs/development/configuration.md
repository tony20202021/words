# Конфигурация с помощью Hydra

## Содержание
1. [Введение](#введение)
2. [Структура конфигурационных файлов](#структура-конфигурационных-файлов)
3. [Использование конфигурации в коде](#использование-конфигурации-в-коде)
4. [Примеры конфигурационных файлов](#примеры-конфигурационных-файлов)
5. [Переопределение конфигурации](#переопределение-конфигурации)
6. [Рекомендации и лучшие практики](#рекомендации-и-лучшие-практики)

## Введение

Проект Language Learning Bot использует библиотеку Hydra для управления конфигурацией. Hydra предоставляет гибкий и модульный подход к управлению настройками приложения через YAML-файлы.

Основные преимущества Hydra:
- **Модульность** - разделение конфигурации на логические компоненты
- **Иерархическая структура** - легкая организация сложных конфигураций
- **Перегрузка параметров** - возможность переопределять параметры из командной строки
- **Композиция конфигураций** - объединение нескольких конфигурационных файлов

## Структура конфигурационных файлов

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

### Фронтенд

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

# Конфигурация изображений
word_images_config = cfg.bot.word_images
image_width = cfg.bot.word_images.width
word_font_size = cfg.bot.word_images.fonts.word_size
```

### Бэкенд

```python
from hydra import compose, initialize

initialize(config_path="../conf/config", version_base=None)
cfg = compose(config_name="default")

# Настройки API
api_host = cfg.api.host
api_port = cfg.api.port

# Настройки базы данных
db_host = cfg.database.mongodb.host
db_port = cfg.database.mongodb.port
db_name = cfg.database.mongodb.db_name
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
  name: "Language Learning Bot"
  environment: "development"
  
# Настройки загрузки файлов
upload:
  folder: "./uploads"
  max_size: 10485760  # 10MB
```

### bot.yaml

```yaml
# Конфигурация бота Telegram

token: ""

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
    description: "Настройки обучения"
  - command: "stats"
    description: "Статистика изучения"
  - command: "show_big"
    description: "Показать крупное изображение слова"

# Настройки для администраторов
admin:
  admin_ids: "1234567,7654321"

# Настройки распознавания речи
voice_recognition:
  enabled: true
  temp_dir: "temp"
  model_size: "small"
  language: "ru"
  max_duration: 60

# Настройки генерации изображений слов
word_images:
  enabled: true
  temp_dir: "temp"
  
  # Размеры изображения
  width: 800
  height: 400
  
  # Размеры шрифтов
  fonts:
    word_size: 240
    transcription_size: 240
  
  # Цвета (RGB значения)
  colors:
    background: [255, 255, 255]  # Белый фон
    text: [50, 50, 50]           # Темно-серый текст
    transcription: [100, 100, 100]  # Серый для транскрипции
  
  # Настройки производительности
  cleanup_delay: 300  # Автоочистка через 5 минут
  save_debug_files: false
```

### api.yaml (frontend)

```yaml
# Конфигурация API-клиента
base_url: "http://localhost:8500"
prefix: "/api"
timeout: 5
retry_count: 3
retry_delay: 1

# Пути API эндпоинтов
endpoints:
  languages:
    list: "/api/languages"
    get: "/api/languages/{id}"
    create: "/api/languages"
  words:
    list: "/api/words"
    get: "/api/words/{id}"
    by_language: "/api/languages/{language_id}/words"
  users:
    list: "/api/users"
    get: "/api/users/{id}"
    stats: "/api/users/{id}/stats"
```

### learning.yaml

```yaml
# Конфигурация процесса обучения

# Настройки по умолчанию
start_word: 1
skip_marked: false
use_check_date: true
max_interval: 32
interval_multiplier: 2
default_interval: 1

# Настройки batch-загрузки
batch:
  limit: 100
  preload_next: true
```

### database.yaml (backend)

```yaml
# Конфигурация базы данных

mongodb:
  host: "localhost"
  port: 27017
  db_name: "language_learning_bot"
  
  # Настройки подключения
  connection:
    max_pool_size: 10
    min_pool_size: 1
    max_idle_time_ms: 30000
    
  # Настройки индексов
  indexes:
    auto_create: true
    background: true
```

### logging.yaml

```yaml
# Конфигурация логирования

level: "INFO"
format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# Настройки файлов логов
files:
  app:
    filename: "logs/app.log"
    max_size: "10MB"
    backup_count: 5
  error:
    filename: "logs/error.log"
    level: "ERROR"
    max_size: "10MB"
    backup_count: 3

# Настройки консольного вывода
console:
  enabled: true
  level: "INFO"
  colorize: true
```

## Переопределение конфигурации

Hydra позволяет переопределять настройки из командной строки:

```bash
# Запуск с переопределением настроек
python app/main.py api.port=8501 logging.level=DEBUG

# Переопределение настроек изображений
python app/main.py bot.word_images.fonts.word_size=300
python app/main.py bot.word_images.enabled=false

# Переопределение настроек базы данных
python app/main.py database.mongodb.host=remote-server
python app/main.py database.mongodb.port=27018
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

```yaml
# bot.yaml.example
token: "${TELEGRAM_BOT_TOKEN}"
admin:
  admin_ids: "${ADMIN_IDS}"
```

### 3. Значения по умолчанию

- Всегда указывайте разумные значения по умолчанию
- Проверяйте наличие обязательных параметров в коде
- Документируйте назначение каждого параметра

### 4. Окружения разработки и продакшена

Создавайте отдельные конфигурации для разных окружений:

```yaml
# default.yaml
defaults:
  - _self_
  - bot
  - api
  - logging
  - learning
  - override hydra/launcher: basic

# Переопределение для продакшена
environment: ${oc.env:ENVIRONMENT,development}

# production.yaml
defaults:
  - default

logging:
  level: "WARNING"
  
api:
  base_url: "https://api.production.com"
  
bot:
  word_images:
    save_debug_files: false
```

### 5. Валидация конфигурации

Добавляйте проверки конфигурации в код:

```python
from omegaconf import OmegaConf

def validate_config(cfg):
    """Валидация конфигурации"""
    
    # Проверка обязательных параметров
    if not cfg.bot.token:
        raise ValueError("Bot token is required")
    
    # Проверка корректности значений
    if cfg.learning.max_interval <= 0:
        raise ValueError("Max interval must be positive")
    
    # Проверка настроек изображений
    if cfg.bot.word_images.enabled:
        if cfg.bot.word_images.width <= 0:
            raise ValueError("Image width must be positive")

# Использование
cfg = compose(config_name="default")
validate_config(cfg)
```
