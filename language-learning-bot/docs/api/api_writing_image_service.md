# Документация API Writing Service

## Общая информация

Writing Service - это микросервис для генерации изображений написания слов, предназначенный для изучения иностранных языков. Сервис предоставляет REST API для создания картинок с различными стилями написания.

- **Базовый URL**: `http://localhost:8600`
- **API префикс**: `/api`
- **Документация API**: `/api/docs` (Swagger UI)
- **Альтернативная документация**: `/api/redoc` (ReDoc)
- **OpenAPI спецификация**: `/api/openapi.json`

## Аутентификация

В текущей версии API не использует аутентификацию. Сервис предназначен для внутреннего использования в рамках Language Learning Bot.

## Общие параметры и ограничения

### Поддерживаемые языки
- **chinese** - Китайский язык
- **japanese** - Японский язык  
- **korean** - Корейский язык
- **english** - Английский язык
- **russian** - Русский язык
- **arabic** - Арабский язык
- **hindi** - Хинди
- **spanish** - Испанский язык
- **french** - Французский язык
- **german** - Немецкий язык
- **italian** - Итальянский язык

### Поддерживаемые стили написания
- **traditional** - Традиционное написание
- **simplified** - Упрощенное написание
- **calligraphy** - Каллиграфическое написание
- **print** - Печатное написание
- **cursive** - Курсивное написание
- **hiragana** - Хирагана (японский)
- **katakana** - Катакана (японский)
- **kanji** - Кандзи (японский)
- **hangul** - Хангыль (корейский)

### Ограничения
- Максимальная длина слова: 50 символов
- Размер изображения: 100x100 - 2048x2048 пикселей
- Качество изображения: 1-100
- Поддерживаемые форматы: PNG, JPEG

## Эндпоинты API

### 1. Health Check Эндпоинты

#### Базовая проверка здоровья

- **URL**: `/health`
- **Метод**: `GET`
- **Описание**: Базовая проверка состояния сервиса
- **Успешный ответ**:
  ```json
  {
    "status": "healthy",
    "service": "writing_image_service",
    "timestamp": "2025-06-06T12:00:00.000Z",
    "uptime_seconds": 3600,
    "version": "1.0.0"
  }
  ```

#### Детальная проверка здоровья

- **URL**: `/health/detailed`
- **Метод**: `GET`
- **Описание**: Подробная информация о состоянии сервиса
- **Успешный ответ**:
  ```json
  {
    "status": "healthy",
    "service": "writing_image_service",
    "timestamp": "2025-06-06T12:00:00.000Z",
    "uptime_seconds": 3600,
    "version": "1.0.0",
    "components": {
      "temp_directory": "ok",
      "image_generation": "ready"
    },
    "system": {
      "memory_percent": 45.2,
      "disk_percent": 23.1,
      "available_memory_mb": 4096,
      "available_disk_gb": 15
    },
    "configuration": {
      "default_image_size": "600x600",
      "supported_formats": ["png", "jpg"],
      "max_concurrent_generations": 5
    }
  }
  ```

#### Проверка готовности (Readiness)

- **URL**: `/health/ready`
- **Метод**: `GET`
- **Описание**: Проверка готовности к обработке запросов
- **Успешный ответ**:
  ```json
  {
    "status": "ready",
    "service": "writing_image_service",
    "timestamp": "2025-06-06T12:00:00.000Z",
    "checks": {
      "temp_directory": "writable",
      "image_generation": "available"
    }
  }
  ```

#### Проверка жизнеспособности (Liveness)

- **URL**: `/health/live`
- **Метод**: `GET`
- **Описание**: Проверка того, что сервис работает
- **Успешный ответ**:
  ```json
  {
    "status": "alive",
    "service": "writing_image_service",
    "timestamp": "2025-06-06T12:00:00.000Z",
    "pid": 12345
  }
  ```

### 2. Генерация Изображений

#### Генерация изображения (JSON ответ)

- **URL**: `/api/writing/generate-writing-image`
- **Метод**: `POST`
- **Описание**: Генерирует изображение написания и возвращает его в формате base64
- **Заголовки запроса**:
  - `Content-Type: application/json`
- **Тело запроса**:
  ```json
  {
    "word": "你好",
    "language": "chinese",
    "style": "traditional",
    "width": 600,
    "height": 600,
    "show_guidelines": true,
    "quality": 90
  }
  ```
- **Параметры запроса**:
  - `word` (обязательный) - Слово для генерации изображения
  - `language` (опциональный) - Код языка (по умолчанию: "chinese")
  - `style` (опциональный) - Стиль написания (по умолчанию: "traditional")
  - `width` (опциональный) - Ширина изображения в пикселях (по умолчанию: 600)
  - `height` (опциональный) - Высота изображения в пикселях (по умолчанию: 600)
  - `show_guidelines` (опциональный) - Показывать направляющие линии (по умолчанию: true)
  - `quality` (опциональный) - Качество изображения 1-100 (по умолчанию: 90)

- **Успешный ответ** (HTTP 200):
  ```json
  {
    "success": true,
    "image_data": "iVBORw0KGgoAAAANSUhEUgAA...",
    "format": "png",
    "metadata": {
      "word": "你好",
      "language": "chinese",
      "style": "traditional",
      "width": 600,
      "height": 600,
      "format": "png",
      "size_bytes": 15234,
      "generation_time_ms": 1500,
      "quality": 90,
      "show_guidelines": true
    },
    "error": null
  }
  ```

- **Ответ при ошибке валидации** (HTTP 400):
  ```json
  {
    "detail": "Validation failed: Word cannot be empty"
  }
  ```

- **Ответ при ошибке генерации** (HTTP 500):
  ```json
  {
    "detail": "Image generation failed: Internal generation error"
  }
  ```

#### Генерация изображения (бинарный ответ)

- **URL**: `/api/writing/generate-writing-image-binary`
- **Метод**: `POST`
- **Описание**: Генерирует изображение написания и возвращает его как бинарные данные
- **Заголовки запроса**:
  - `Content-Type: application/json`
- **Тело запроса**: То же самое, что для JSON эндпоинта
- **Успешный ответ** (HTTP 200):
  - `Content-Type: image/png` (или `image/jpeg`)
  - **Заголовки ответа**:
    - `Content-Disposition: attachment; filename=writing_测试.png`
    - `X-Word: 测试`
    - `X-Language: chinese`
    - `X-Style: traditional`
  - **Тело**: Бинарные данные изображения

#### Получение статуса сервиса

- **URL**: `/api/writing/status`
- **Метод**: `GET`
- **Описание**: Получает информацию о состоянии и конфигурации сервиса генерации
- **Успешный ответ**:
  ```json
  {
    "success": true,
    "status": 200,
    "result": {
      "service": "writing_image_service",
      "status": "healthy",
      "version": "1.0.0",
      "uptime_seconds": 7200,
      "total_generations": 150,
      "implementation": "stub",
      "supported_languages": [
        "chinese", "japanese", "korean", "english", 
        "russian", "arabic", "hindi", "spanish", "french"
      ],
      "supported_formats": ["png"],
      "max_image_size": {"width": 2048, "height": 2048},
      "default_image_size": {"width": 600, "height": 600}
    },
    "error": null
  }
  ```

## Модели данных

### WritingImageRequest

```json
{
  "word": "string (1-50 символов, обязательно)",
  "language": "string (код языка, по умолчанию: 'chinese')",
  "style": "string (стиль написания, по умолчанию: 'traditional')",
  "width": "integer (100-2048, по умолчанию: 600)",
  "height": "integer (100-2048, по умолчанию: 600)",
  "show_guidelines": "boolean (по умолчанию: true)",
  "quality": "integer (1-100, по умолчанию: 90)"
}
```

### WritingImageMetadata

```json
{
  "word": "string",
  "language": "string",
  "style": "string",
  "width": "integer",
  "height": "integer",
  "format": "string",
  "size_bytes": "integer",
  "generation_time_ms": "integer",
  "quality": "integer",
  "show_guidelines": "boolean"
}
```

### WritingImageResponse

```json
{
  "success": "boolean",
  "image_data": "string (base64) | null",
  "format": "string",
  "metadata": "WritingImageMetadata | null",
  "error": "string | null"
}
```

## Примеры использования

### Генерация простого изображения

```bash
curl -X POST http://localhost:8600/api/writing/generate-writing-image \
  -H "Content-Type: application/json" \
  -d '{
    "word": "hello",
    "language": "english",
    "style": "print"
  }'
```

### Генерация китайского иероглифа с направляющими

```bash
curl -X POST http://localhost:8600/api/writing/generate-writing-image \
  -H "Content-Type: application/json" \
  -d '{
    "word": "学习",
    "language": "chinese",
    "style": "traditional",
    "width": 800,
    "height": 800,
    "show_guidelines": true,
    "quality": 95
  }'
```

### Скачивание изображения как файла

```bash
curl -X POST http://localhost:8600/api/writing/generate-writing-image-binary \
  -H "Content-Type: application/json" \
  -d '{
    "word": "書く",
    "language": "japanese",
    "style": "kanji"
  }' \
  --output writing_kanji.png
```

### Проверка поддерживаемых языков

```bash
curl http://localhost:8600/api/writing/status | jq '.result.supported_languages'
```

## Интеграция с основным проектом

### Использование во фронтенде (Telegram-бот)

Writing Service интегрируется с основным ботом через API клиент:

```python
from app.api.client import APIClient

api_client = APIClient()

# Генерация изображения написания
response = await api_client.generate_writing_image(
    word="测试",
    language="chinese",
    style="traditional"
)

if response["success"]:
    image_data = response["result"]["image_data"]
    # Отправка изображения пользователю
else:
    error = response.get("error", "Unknown error")
    # Обработка ошибки
```

### Конфигурация в основном проекте

В фронтенде настройки Writing Service задаются через конфигурацию:

```yaml
# frontend/conf/config/api.yaml
writing_service:
  base_url: "http://localhost:8600"
  timeout: 30
  retry_count: 3
  default_language: "chinese"
  default_style: "traditional"
```

## Обработка ошибок

### Типы ошибок

1. **Ошибки валидации (400)**:
   - Пустое слово
   - Неподдерживаемый язык или стиль
   - Некорректные размеры изображения
   - Недопустимое качество изображения

2. **Ошибки генерации (500)**:
   - Ошибка создания изображения
   - Проблемы с временными файлами
   - Внутренние ошибки сервиса

3. **Ошибки сервиса (503)**:
   - Сервис временно недоступен
   - Превышен лимит одновременных запросов

4. **Ошибки лимитов (429)**:
   - Превышен лимит запросов (если включен rate limiting)

### Примеры ответов с ошибками

**Ошибка валидации:**
```json
{
  "detail": "Validation failed: Word cannot be empty, Width must be at least 100 pixels"
}
```

**Ошибка генерации:**
```json
{
  "detail": "Image generation failed: Unable to create temporary file"
}
```

**Сервис недоступен:**
```json
{
  "detail": "Service is currently unavailable: Temporary directory not accessible"
}
```

## Мониторинг и логирование

### Логирование

Writing Service ведет подробные логи всех операций:

```bash
# Просмотр логов в реальном времени
tail -f writing_service/logs/writing_service.log

# Поиск ошибок в логах
grep "ERROR" writing_service/logs/writing_service.log

# Поиск запросов генерации
grep "Generating writing image" writing_service/logs/writing_service.log
```

### Метрики производительности

Каждый ответ содержит метаданные с информацией о производительности:

- `generation_time_ms` - время генерации в миллисекундах
- `size_bytes` - размер изображения в байтах
- Время отклика HTTP запроса

### Health Check для мониторинга

Для систем мониторинга рекомендуется использовать специализированные эндпоинты:

```bash
# Для Kubernetes liveness probe
curl http://localhost:8600/health/live

# Для Kubernetes readiness probe  
curl http://localhost:8600/health/ready

# Для детального мониторинга
curl http://localhost:8600/health/detailed
```

## Конфигурация сервиса

### Переменные окружения

Writing Service может настраиваться через переменные окружения:

```bash
# Основные настройки
WRITING_SERVICE_HOST=0.0.0.0
WRITING_SERVICE_PORT=8600
API_PREFIX=/api
DEBUG=true

# Настройки CORS
CORS_ORIGINS=*

# Настройки логирования
LOG_LEVEL=INFO
LOG_DIR=logs

# Настройки генерации
DEFAULT_IMAGE_WIDTH=600
DEFAULT_IMAGE_HEIGHT=600
MAX_WORD_LENGTH=50
```

### Конфигурация через Hydra

Альтернативно, сервис использует конфигурационные файлы Hydra:

```yaml
# writing_service/conf/config/default.yaml
app:
  name: "Writing Image Service"
  environment: "development"

api:
  host: "0.0.0.0"
  port: 8600
  prefix: "/api"
  debug: true

generation:
  defaults:
    width: 600
    height: 600
    quality: 90
    style: "traditional"
```

## Развертывание

### Docker контейнер

```dockerfile
# Dockerfile для Writing Service
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY writing_service/ ./writing_service/
COPY common/ ./common/

EXPOSE 8600

CMD ["python", "-m", "writing_service.app.main_writing_service"]
```

### Docker Compose

```yaml
# docker-compose.yml (фрагмент)
services:
  writing-service:
    build: .
    ports:
      - "8600:8600"
    environment:
      - WRITING_SERVICE_HOST=0.0.0.0
      - WRITING_SERVICE_PORT=8600
      - LOG_LEVEL=INFO
    volumes:
      - ./writing_service/logs:/app/writing_service/logs
      - ./writing_service/temp:/app/writing_service/temp
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8600/health"]
      interval: 30s
      timeout: 10s
      retries: 3
```

### Kubernetes развертывание

```yaml
# writing-service-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: writing-service
spec:
  replicas: 2
  selector:
    matchLabels:
      app: writing-service
  template:
    metadata:
      labels:
        app: writing-service
    spec:
      containers:
      - name: writing-service
        image: language-learning-bot/writing-service:latest
        ports:
        - containerPort: 8600
        env:
        - name: WRITING_SERVICE_PORT
          value: "8600"
        - name: LOG_LEVEL
          value: "INFO"
        livenessProbe:
          httpGet:
            path: /health/live
            port: 8600
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health/ready
            port: 8600
          initialDelaySeconds: 5
          periodSeconds: 5
        resources:
          requests:
            memory: "256Mi"
            cpu: "100m"
          limits:
            memory: "512Mi"
            cpu: "500m"
```

## Производительность и масштабирование

### Рекомендации по производительности

1. **Кэширование**: Рассмотрите возможность кэширования часто запрашиваемых изображений
2. **Batch операции**: Используйте batch API для генерации множества изображений
3. **Асинхронная обработка**: Для большого объема запросов используйте очереди
4. **Мониторинг ресурсов**: Отслеживайте использование CPU и памяти

### Горизонтальное масштабирование

Writing Service спроектирован как stateless микросервис и может быть легко масштабирован:

```bash
# Запуск дополнительных экземпляров на разных портах
./start_4_writing_service.sh --port=8601
./start_4_writing_service.sh --port=8602
./start_4_writing_service.sh --port=8603
```

### Load Balancer конфигурация

```nginx
# nginx.conf (фрагмент)
upstream writing_service {
    server localhost:8600;
    server localhost:8601;
    server localhost:8602;
}

server {
    listen 80;
    location /api/writing/ {
        proxy_pass http://writing_service;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## Будущие возможности

### Планируемые функции

1. **Реальная генерация изображений**: Замена stub-реализации на настоящую генерацию с использованием шрифтов
2. **Batch API**: Генерация множества изображений за один запрос
3. **Кэширование**: Система кэширования готовых изображений
4. **Дополнительные форматы**: Поддержка SVG, WebP
5. **Анимированные изображения**: Пошаговая анимация написания
6. **Пользовательские шрифты**: Загрузка и использование собственных шрифтов

### Extensibility

Сервис спроектирован для легкого расширения:

- Модульная архитектура позволяет добавлять новые типы генераторов
- Система валидации легко настраивается для новых языков
- API версионирование для обратной совместимости

## Заключение

Writing Service предоставляет мощный и гибкий API для генерации изображений написания в рамках системы изучения языков. Текущая stub-реализация обеспечивает полную функциональность API и может быть легко заменена на реальную генерацию изображений без изменения интерфейса.

Для получения актуальной информации и интерактивного тестирования API используйте Swagger UI по адресу: `http://localhost:8600/api/docs`
