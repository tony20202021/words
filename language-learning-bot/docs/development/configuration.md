# Конфигурация с помощью Hydra (обновлено с системой изображений)

## Содержание
1. [Введение](#введение)
2. [Структура конфигурационных файлов](#структура-конфигурационных-файлов)
3. [Использование конфигурации в коде](#использование-конфигурации-в-коде)
4. [Примеры конфигурационных файлов](#примеры-конфигурационных-файлов)
5. [Переопределение конфигурации](#переопределение-конфигурации)
6. [Рекомендации и лучшие практики](#рекомендации-и-лучшие-практики)

## Введение

Проект Language Learning Bot использует библиотеку Hydra для управления конфигурацией. Hydra предоставляет гибкий и модульный подход к управлению настройками приложения через YAML-файлы, позволяя разделить конфигурацию на логические группы и файлы.

Основные преимущества Hydra:
- Модульность - разделение конфигурации на логические компоненты
- Иерархическая структура - легкая организация сложных конфигураций
- Перегрузка параметров - возможность переопределять параметры из командной строки
- Композиция конфигураций - объединение нескольких конфигурационных файлов

## Структура конфигурационных файлов

Конфигурация разделена на несколько файлов, расположенных в директориях:

### Фронтенд (frontend/conf/config/)

- **default.yaml** - основной файл, подключающий другие конфигурационные файлы
- **bot.yaml** - настройки Telegram-бота **ОБНОВЛЕНО: с конфигурацией изображений**
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

# НОВОЕ: Конфигурация изображений
word_images_config = cfg.bot.word_images
image_width = cfg.bot.word_images.width
word_font_size = cfg.bot.word_images.fonts.word_size
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
  - command: "hint"
    description: "Информация о подсказках"
  - command: "admin"
    description: "Режим администратора"

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

# НОВОЕ: Настройки генерации изображений слов
word_images:
  # Основные настройки
  enabled: true
  temp_dir: "temp"
  
  # Размеры изображения
  width: 800
  height: 400
  
  # Размеры шрифтов (стартовые, автоподбираются при необходимости)
  fonts:
    word_size: 240           # Размер шрифта для слова
    transcription_size: 240  # Размер шрифта для транскрипции
  
  # Цвета (RGB значения)
  colors:
    background: [255, 255, 255]  # Белый фон
    text: [50, 50, 50]           # Темно-серый текст
    transcription: [100, 100, 100]  # Серый для транскрипции
    border: [200, 200, 200]      # Светло-серая рамка
  
  # Настройки производительности
  cleanup_delay: 300  # Автоочистка временных файлов через 5 минут
  save_debug_files: false  # Сохранение файлов для отладки
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

# Настройки процесса обучения (значения по умолчанию)
start_word: 1
skip_marked: false
use_check_date: true
max_interval: 32
interval_multiplier: 2
default_interval: 1
```

## Переопределение конфигурации

Hydra позволяет переопределять настройки из командной строки:

```bash
# Запуск с переопределением настроек
python app/main.py api.port=8501 logging.level=DEBUG

# Переопределение настроек изображений
python app/main.py bot.word_images.fonts.word_size=300
python app/main.py bot.word_images.enabled=false
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

### 3. Значения по умолчанию

- Всегда указывайте разумные значения по умолчанию
- Проверяйте наличие обязательных параметров в коде
- Документируйте назначение каждого параметра


##
frontend/app/main_frontend.py

from app.utils import config_holder
# Initialize Hydra configuration
with initialize(config_path="../conf/config", version_base=None):
    config_holder.cfg = compose(config_name="default")
cfg = config_holder.cfg

WordImageGenerator
from app.utils import config_holder
logger.info(f"WordImageGenerator.config: {config_holder.cfg.bot.word_images}")
