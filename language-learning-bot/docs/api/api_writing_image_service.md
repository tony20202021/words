# Документация API Writing Service

## Общая информация

Writing Service - это микросервис для генерации изображений написания слов с **универсальной поддержкой всех языков**. Сервис автоматически адаптируется к любому языку и не имеет ограничений по поддерживаемым языкам.

- **Базовый URL**: `http://localhost:8600`
- **API префикс**: `/api`
- **Документация API**: `/api/docs` (Swagger UI)
- **Альтернативная документация**: `/api/redoc` (ReDoc)
- **OpenAPI спецификация**: `/api/openapi.json`

## Аутентификация

В текущей версии API не использует аутентификацию. Сервис предназначен для внутреннего использования в рамках Language Learning Bot.

## Универсальная поддержка языков

### Ключевые особенности

- **Все языки поддерживаются** - нет ограничений или черных списков
- **Автоматическая адаптация** - сервис автоматически подбирает подходящие шрифты
- **Unicode поддержка** - полная поддержка всех Unicode символов
- **Гибкая валидация** - принимаются любые разумные языковые коды

### Поддерживаемые форматы языков

- Стандартные коды: `chinese`, `english`, `russian`, `arabic`, `hindi`
- ISO коды: `zh`, `en`, `ru`, `ar`, `hi` 
- Региональные варианты: `zh-cn`, `zh-tw`, `en-us`, `en-gb`
- Пользовательские названия: `mandarin`, `cantonese`, `simplified_chinese`

## Общие параметры и ограничения

### Параметры изображения
- Размер изображения: 100x100 - 2048x2048 пикселей
- Качество изображения: 1-100
- Поддерживаемые форматы: PNG, JPEG
- Максимальная длина слова: 50 символов

### Стили написания
Сервис принимает **любые стили написания**. Общие стили включают:
- `traditional`, `simplified`, `calligraphy`, `print`, `cursive`
- `hiragana`, `katakana`, `kanji`, `hangul`
- `naskh`, `nastaliq`, `devanagari`
- И любые другие пользовательские стили

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
    "timestamp": "2025-06-08T12:00:00.000Z",
    "uptime_seconds": 3600,
    "version": "1.0.0"
  }
  ```

### 2. Генерация Изображений

#### Генерация изображения (JSON ответ)
- **URL**: `/api/writing/generate-writing-image`
- **Метод**: `POST`
- **Описание**: Генерирует изображение написания для любого языка
- **Тело запроса**:
  ```json
  {
    "word": "任何语言",
    "language": "any_language",
    "style": "any_style",
    "width": 600,
    "height": 600,
    "show_guidelines": true,
    "quality": 90
  }
  ```

#### Генерация изображения (бинарный ответ)
- **URL**: `/api/writing/generate-writing-image-binary`
- **Метод**: `POST`
- **Описание**: Генерирует изображение и возвращает как бинарные данные

#### Получение статуса сервиса
- **URL**: `/api/writing/status`
- **Метод**: `GET`
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
      "implementation": "stub_with_image_processor",
      "supported_formats": ["png"],
      "max_image_size": {"width": 2048, "height": 2048},
      "default_image_size": {"width": 600, "height": 600},
      "features": {
        "guidelines": true,
        "borders": true,
        "text_centering": true,
        "async_processing": true,
        "universal_language_support": true
      }
    }
  }
  ```

## Примеры использования

### Генерация китайского иероглифа
```bash
curl -X POST http://localhost:8600/api/writing/generate-writing-image \
  -H "Content-Type: application/json" \
  -d '{
    "word": "学习",
    "language": "chinese",
    "style": "traditional"
  }'
```

## Обработка ошибок

### Типы ошибок

1. **Ошибки валидации (400)**:
   - Пустое слово
   - Некорректные размеры изображения
   - Недопустимое качество изображения
   - Слишком длинное слово

2. **Ошибки генерации (500)**:
   - Ошибка создания изображения
   - Проблемы с временными файлами
   - Внутренние ошибки сервиса

### Примеры ответов с ошибками

**Ошибка валидации:**
```json
{
  "detail": "Validation failed: Word cannot be empty, Width must be at least 100 pixels"
}
```

**Предупреждения (не ошибки):**
```json
{
  "success": true,
  "warnings": [
    "Language 'elvish' may not be fully supported",
    "Style 'mystical' is not commonly used, but will be accepted"
  ]
}
```

## Интеграция с основным проектом

### Использование во фронтенде

```python
from app.api.client import APIClient

api_client = APIClient()

# Генерация для любого языка
response = await api_client.generate_writing_image(
    word="任何词汇",
    language="any_language",  # Любой язык принимается
    style="any_style"         # Любой стиль принимается
)
```

### Конфигурация универсальной поддержки

```yaml
# frontend/conf/config/api.yaml
writing_service:
  base_url: "http://localhost:8600"
  timeout: 30
  retry_count: 3
  default_language: "auto"          # Автоопределение
  default_style: "traditional"
  universal_support: true          # Все языки поддерживаются
  auto_font_detection: true        # Автоматический выбор шрифта
```

## Архитектурные особенности

### Общий FontManager
Сервис использует общий модуль `common/utils/font_utils.py`:

```python
# common/utils/font_utils.py
class FontManager:
    """Универсальный менеджер шрифтов для всех языков"""
    
    def get_unicode_font_paths(self) -> List[str]:
        """Поиск Unicode шрифтов для всех языков"""
        pass
    
    async def auto_fit_font_size(self, text: str, max_width: int, max_height: int):
        """Автоподбор размера для любого текста"""
        pass
```

### ImageProcessor интеграция
```python
# writing_service/app/utils/image_utils.py
from common.utils.font_utils import get_font_manager

class ImageProcessor:
    def __init__(self):
        self.font_manager = get_font_manager()  # Общий менеджер
    
    async def add_auto_fit_text(self, image, text, max_width, max_height):
        """Автоподбор текста с универсальной поддержкой"""
        pass
```

## Мониторинг универсальной поддержки

### Метрики поддержки языков
```bash
# Проверка статистики поддержки языков
curl http://localhost:8600/api/writing/status | jq '.result.features.universal_language_support'
# Ответ: true

# Проверка автоматического выбора шрифтов
curl http://localhost:8600/api/writing/status | jq '.result.features'
```

### Логирование языков
```bash
# Просмотр логов генерации для разных языков
grep "Generating writing image" writing_service/logs/writing_service.log

# Поиск предупреждений о языках
grep "Language.*may not be fully supported" writing_service/logs/writing_service.log
```

## Заключение

Writing Service предоставляет **универсальную поддержку всех языков** без ограничений. Сервис автоматически адаптируется к любому языку и стилю написания, используя общий FontManager и продвинутую систему обработки Unicode.

Для получения актуальной информации используйте: `http://localhost:8600/api/docs`
