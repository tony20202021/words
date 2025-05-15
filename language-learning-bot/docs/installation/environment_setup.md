# Настройка окружения

Данный документ содержит подробную информацию о настройке окружения для проекта Language Learning Bot.

## Содержание
1. [Управление зависимостями](#управление-зависимостями)
2. [Переменные окружения](#переменные-окружения)
3. [Конфигурация с помощью Hydra](#конфигурация-с-помощью-hydra)
4. [Настройки для разработки](#настройки-для-разработки)
5. [Настройки для production](#настройки-для-production)

## Управление зависимостями

### Conda

Проект использует Conda для управления зависимостями и создания изолированных окружений.

#### Создание окружения

```bash
# Создание окружения из файла environment.yml
conda env create -f environment.yml

# Активация окружения
conda activate language-learning-bot
```

#### Обновление окружения

Если файл `environment.yml` был обновлен:

```bash
conda env update -f environment.yml
```

#### Управление дополнительными пакетами

```bash
# Установка нового пакета
conda install -n language-learning-bot package_name

# Удаление пакета
conda remove -n language-learning-bot package_name
```

### Pip

Если вы используете pip вместо Conda:

```bash
# Установка всех зависимостей
pip install -r requirements.txt

# Установка дополнительного пакета
pip install package_name

# Обновление зависимостей
pip install -r requirements.txt --upgrade
```

## Переменные окружения

### Файл .env

Проект использует `.env` файл для хранения переменных окружения. Создайте его из примера:

```bash
cp .env.example .env
```

### Основные переменные окружения

```
# MongoDB
MONGODB_HOST=localhost      # Хост MongoDB
MONGODB_PORT=27017          # Порт MongoDB
MONGODB_DB_NAME=language_learning_bot  # Имя базы данных

# Telegram
TELEGRAM_BOT_TOKEN=your_token_here  # Токен бота Telegram
```

### Экспорт переменных окружения

Для загрузки переменных окружения из файла `.env` используйте скрипт `run_export_env.sh`:

```bash
# Сделать скрипт исполняемым
chmod +x run_export_env.sh

# Загрузить переменные окружения
source ./run_export_env.sh
```

Важно использовать команду `source` вместо простого запуска скрипта, чтобы переменные экспортировались в текущую сессию.

## Конфигурация с помощью Hydra

Проект использует Hydra для управления конфигурацией.

### Структура конфигурационных файлов

#### Фронтенд (frontend/conf/config/)

- **default.yaml** - основной файл, подключающий другие файлы
- **bot.yaml** - настройки Telegram-бота
- **api.yaml** - настройки для подключения к бэкенду
- **logging.yaml** - настройки логирования
- **learning.yaml** - настройки процесса обучения

#### Бэкенд (backend/conf/config/)

- **default.yaml** - основной файл, подключающий другие файлы
- **api.yaml** - настройки API-сервера (хост, порт, CORS)
- **database.yaml** - настройки подключения к MongoDB
- **logging.yaml** - настройки логирования

### Настройка основных компонентов

#### Настройка Telegram-бота

Отредактируйте файл `frontend/conf/config/bot.yaml`:

```yaml
# Токен для подключения к Telegram API
token: "YOUR_TELEGRAM_BOT_TOKEN"

# Настройки бота
skip_updates: true
polling_timeout: 30
retry_timeout: 5

# Список команд бота
commands:
  - command: "start"
    description: "Начать работу с ботом"
  - command: "help"
    description: "Получить справку"
  # ... другие команды
```

#### Настройка API бэкенда

Отредактируйте файл `frontend/conf/config/api.yaml`:

```yaml
# Конфигурация API-клиента
base_url: "http://localhost:8500"  # URL бэкенда
prefix: "/api"                     # Префикс API
timeout: 5                         # Таймаут запросов в секундах
retry_count: 3                     # Число повторных попыток
```

#### Настройка базы данных

Отредактируйте файл `backend/conf/config/database.yaml`:

```yaml
# Конфигурация базы данных
type: "mongodb"  # Тип базы данных

# Настройки MongoDB
mongodb:
  url: "mongodb://localhost:27017"  # URL подключения
  db_name: "language_learning_bot"  # Имя базы данных
  host: "localhost"                 # Хост MongoDB
  port: 27017                       # Порт MongoDB
```

## Настройки для разработки

### Режим отладки

#### Бэкенд

Для запуска бэкенда в режиме отладки:

```yaml
# В файле backend/conf/config/api.yaml
debug: true      # Режим отладки
```

#### Фронтенд

Для более подробного логирования в фронтенде:

```yaml
# В файле frontend/conf/config/logging.yaml
level: "DEBUG"   # Уровень логирования (DEBUG, INFO, WARNING, ERROR)
```

### Автоматический перезапуск

Для разработки и тестирования можно использовать режим автоматического перезапуска фронтенда:

```bash
# Установка watchdog
chmod +x setup_watchdog.sh
./setup_watchdog.sh

# Запуск с автоперезапуском
chmod +x start_3_frontend_auto_reload.sh
./start_3_frontend_auto_reload.sh
```

## Настройки для production

### Логирование

Для production рекомендуется настроить логирование с ротацией файлов:

```yaml
# В файле frontend/conf/config/logging.yaml и backend/conf/config/logging.yaml
level: "INFO"               # Уровень логирования
log_to_file: true           # Записывать логи в файл
log_file_max_size: 5242880  # 5 MB
log_file_backup_count: 10   # Количество бэкапов при ротации
```

### Безопасность

Для production важно настроить параметры безопасности:

```yaml
# В файле backend/conf/config/api.yaml
cors_origins: "https://your-domain.com"  # Ограничьте CORS
secret_key: "your-secure-secret-key"     # Используйте сложный ключ
```

### Оптимизация производительности

Для оптимизации работы в production:

```yaml
# Настройки пула соединений MongoDB
# В файле backend/conf/config/database.yaml
mongodb:
  min_pool_size: 10
  max_pool_size: 50
  connection_timeout_ms: 2000
```

## Проверка конфигурации

После настройки окружения рекомендуется проверить корректность конфигурации:

### Проверка переменных окружения

```bash
# Загрузить переменные окружения
source ./run_export_env.sh

# Проверить значения
echo $MONGODB_HOST
echo $MONGODB_PORT
echo $MONGODB_DB_NAME
echo $TELEGRAM_BOT_TOKEN
```

### Проверка конфигурации Hydra

```python
# Создайте файл check_config.py
cat > check_config.py << 'EOL'
from hydra import compose, initialize
from omegaconf import OmegaConf
import sys

component = sys.argv[1] if len(sys.argv) > 1 else "frontend"
path = f"../{component}/conf/config"

print(f"Проверка конфигурации для {component} из пути {path}")
try:
    initialize(config_path=path, version_base=None)
    cfg = compose(config_name="default")
    print(OmegaConf.to_yaml(cfg))
    print("Конфигурация загружена успешно!")
except Exception as e:
    print(f"Ошибка при загрузке конфигурации: {e}")
EOL

# Запустите проверку
python check_config.py frontend
python check_config.py backend
```

## Резервное копирование конфигурации

Рекомендуется создать резервные копии файлов конфигурации:

```bash
# Создание бэкапа конфигурации
mkdir -p config_backup/$(date +%Y%m%d)
cp -r frontend/conf/config config_backup/$(date +%Y%m%d)/frontend
cp -r backend/conf/config config_backup/$(date +%Y%m%d)/backend
cp .env config_backup/$(date +%Y%m%d)/
```

### 4.2. Обновление environment_setup.md

Добавить раздел о настройке распознавания речи:

```markdown
### Настройка распознавания речи

Проект использует модель Whisper от OpenAI для распознавания голосовых сообщений. Необходимо настроить параметры распознавания:

```yaml
# В файле frontend/conf/config/bot.yaml
voice_recognition:
  # Размер модели Whisper (tiny, base, small, medium, large)
  model_size: "small"  
  # Язык распознавания (ru для русского)
  language: "ru"        
  # Директория для временных аудиофайлов
  temp_dir: "temp"      
  # Максимальная длительность голосового сообщения в секундах
  max_duration: 60
```
