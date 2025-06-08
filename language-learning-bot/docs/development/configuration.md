# Конфигурация с помощью Hydra

## Содержание
1. [Введение](#введение)
2. [Структура конфигурационных файлов](#структура-конфигурационных-файлов)
3. [Использование конфигурации в коде](#использование-конфигурации-в-коде)
4. [Примеры конфигурационных файлов](#примеры-конфигурационных-файлов)
5. [Переопределение конфигурации](#переопределение-конфигурации)

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

### Writing Service (writing_service/conf/config/)

- **default.yaml** - основной файл сервиса генерации картинок
- **api.yaml** - настройки API сервиса (порт 8600)
- **generation.yaml** - настройки генерации изображений
- **logging.yaml** - настройки логирования сервиса

## Использование конфигурации в коде

from app.utils import config_holder
with initialize(config_path="../conf/config", version_base=None):
    config_holder.cfg = compose(config_name="default")
cfg = config_holder.cfg


## Переопределение конфигурации

Hydra позволяет переопределять настройки из командной строки:

```bash
# Запуск с переопределением настроек
python app/main.py api.port=8501 logging.level=DEBUG

# Переопределение настроек изображений
python app/main.py bot.word_images.fonts.word_size=300
python app/main.py bot.word_images.universal_language_support=false

# Переопределение настроек Writing Service
python app/main_writing_service.py api.port=8601
python app/main_writing_service.py generation.generation_defaults.width=800

# Переопределение настроек базы данных
python app/main.py database.mongodb.host=remote-server
python app/main.py database.mongodb.port=27018
```
