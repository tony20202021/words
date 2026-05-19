# Документация API Writing Images Service

## Общая информация

Writing Images Service - это AI микросервис для генерации изображений написания слов. Использует Stable Diffusion XL + Union ControlNet и Translation Service для перевода русских значений в английские промпты.

- **Базовый URL**: `http://localhost:8600`
- **API префикс**: `/api`
- **Документация API**: `/api/docs` (Swagger UI)
- **Альтернативная документация**: `/api/redoc` (ReDoc)

## 🆕 Translation Service Integration

### Workflow перевода:
```
Русский текст → Translation Service → Английский промпт → AI Generation
```

### Поддерживаемые Translation модели:
- **Qwen2-7B/1.5B** - приоритетные модели для CJK языков
- **NLLB-3.3B/1.3B** - Meta multilingual translation
- **mT5-XL/Large** - Google text-to-text generation
- **OPUS-MT** - легкие специализированные модели

## AI Generation Эндпоинты (с Translation)

### Генерация изображения (JSON ответ)
- **URL**: `/api/writing/generate-writing-image`
- **Метод**: `POST`
- **Описание**: Генерирует AI изображение с автоматическим переводом русского текста

**Тело запроса:**
```json
{
  "word": "学习",
  "translation": "изучение",
  "language": "chinese",
  "style": "comic",
  "width": 1024,
  "height": 1024,
  
  // 🆕 Translation параметры
  "include_translation": true,
  "translation_model": "auto",
  "translation_cache": true,
  
  // 🆕 AI параметры
  "include_conditioning_images": false,
  "include_prompt": true,
  "seed": null
}
```

**🆕 Translation параметры:**

| Параметр | Тип | Описание | По умолчанию |
|----------|-----|----------|--------------|
| `include_translation` | boolean | Включать ли translation метаданные в ответ | `true` |
| `translation_model` | string | Модель перевода (`auto`, `qwen2_7b`, `nllb_3_3b`, `mt5_xl`) | `"auto"` |
| `translation_cache` | boolean | Использовать ли кэш переводов | `true` |
| `translation_fallback` | boolean | Fallback к оригинальному тексту при ошибке | `true` |

**🆕 AI параметры:**

| Параметр | Тип | Описание | По умолчанию |
|----------|-----|----------|--------------|
| `include_conditioning_images` | boolean | Включать conditioning изображения | `false` |
| `include_prompt` | boolean | Включать финальный промпт | `true` |
| `seed` | integer/null | Seed для воспроизводимости | `null` |

**Успешный ответ:**
```json
{
  "success": true,
  "status": "SUCCESS",
  "generated_image_base64": "iVBORw0KGgoAAAANS...",
  
  // 🆕 Translation данные
  "translation_used": "learning, study",
  "translation_source": "ai_model",
  "translation_time_ms": 250,
  
  // 🆕 AI метаданные
  "prompt_used": "A vibrant comic book style illustration of learning, study, inspired by Chinese character 学习",
  "generation_metadata": {
    "character": "学习",
    "original_translation": "изучение",
    "english_translation": "learning, study",
    "translation_metadata": {
      "source": "ai_model",
      "model_used": "Qwen/Qwen2-7B-Instruct",
      "cache_hit": false,
      "confidence_score": 0.92
    },
    "generation_time_ms": 8500,
    "model_used": "stabilityai/stable-diffusion-xl-base-1.0",
    "controlnet_model": "union",
    "conditioning_types_used": ["canny"],
    "seed_used": null
  },
  
  "error": null,
  "warnings": null
}
```

### Генерация изображения (бинарный ответ)
- **URL**: `/api/writing/generate-writing-image-binary`
- **Метод**: `POST`
- **Описание**: Генерирует изображение и возвращает бинарные данные

**Headers в ответе:**
```
Content-Type: image/png
X-Translation-Used: learning, study
X-Translation-Source: ai_model
X-Translation-Time-Ms: 250
X-Generation-Time-Ms: 8500
X-Model-Used: union
```

## Health Check Эндпоинты

### Детальная проверка здоровья
- **URL**: `/health/detailed`
- **Метод**: `GET`

**Ответ с Translation Service:**
```json
{
  "status": "healthy_with_ai_translation",
  "service": "writing_image_service",
  "timestamp": "2025-06-13T12:00:00.000Z",
  "uptime_seconds": 7200,
  "
  ai_status": {
    "models_loaded": true,
    "pipeline_ready": true,
    "generation_count": 125,
    "average_generation_time_ms": 8200
  },
  
  // 🆕 Translation Service статус
  "translation_service": {
    "enabled": true,
    "initialized": true,
    "active_model": "qwen2_7b",
    "model_loaded": true,
    "translation_count": 125,
    "average_translation_time_ms": 220,
    "cache_hit_rate": 0.68
  },
  
  "gpu_status": {
    "available": true,
    "device_name": "NVIDIA RTX 4090",
    "total_memory_gb": 24.0,
    "used_memory_gb": 18.2,
    "utilization_percent": 75.8
  },
  
  "features": {
    "ai_generation": true,
    "translation_service": true,
    "controlnet_union": true,
    "multi_language_support": true,
    "caching": true
  }
}
```

## Примеры использования

### Генерация изображения
```bash
curl -X POST http://localhost:8600/api/writing/generate-writing-image \
  -H "Content-Type: application/json" \
  -d '{
    "word": "美丽",
    "translation": "красивый",
    "style": "watercolor",
    "include_prompt": true
  }'
```

### Генерация (бинарный ответ)
```bash
curl -X POST http://localhost:8600/api/writing/generate-writing-image-binary \
  -H "Content-Type: application/json" \
  -d '{"word": "学习", "translation": "учёба"}' \
  --output image.png
```

### Проверка здоровья
```bash
curl http://localhost:8600/health
curl http://localhost:8600/health/detailed
curl http://localhost:8600/health/ready
curl http://localhost:8600/health/live
```

## Обработка ошибок (обновлено)

### 🆕 Translation ошибки (400)
- Translation model not available
- Translation service not ready
- Invalid translation parameters
- Translation timeout

### 🆕 AI + Translation ошибки (500)
- Translation service failed
- AI generation with translation failed
- GPU memory insufficient for both models
- Model loading conflicts

**Пример ответа с Translation ошибкой:**
```json
{
  "success": false,
  "error": "Translation failed: Model qwen2_7b not loaded",
  "translation_fallback": "красивый",
  "generation_metadata": {
    "translation_error": true,
    "fallback_used": true
  }
}
```

## Performance Metrics (обновлено)

### 🆕 Timing Breakdown
```
Total Time: ~8.5s (RTX 4090)
├── Translation: ~0.2s (Qwen2-7B warm)
├── Preprocessing: ~0.1s
├── Conditioning: ~0.5s
├── AI Generation: ~7.5s
└── Postprocessing: ~0.2s
```

### 🆕 Memory Usage
```
80GB VRAM: SDXL(6GB) + ControlNet(2GB) + Qwen2-7B(14GB) = ~22GB
40GB VRAM: SDXL(6GB) + ControlNet(2GB) + NLLB-3.3B(7GB) = ~15GB
24GB VRAM: SDXL(6GB) + ControlNet(2GB) + mT5-Large(3GB) = ~11GB
```

## Configuration

### 🆕 Translation настройки
```yaml
# writing_images_service/conf/config/translation.yaml
translation:
  enabled: true
  active_model: "qwen2_7b"
  auto_model_selection: true
  caching:
    enabled: true
    max_cache_size: 10000
    cache_ttl_hours: 168
```

Для полной документации: `http://localhost:8600/api/docs`
