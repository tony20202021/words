# Документация API Writing Service (ОБНОВЛЕНО с Translation Service)

## Общая информация

Writing Service - это AI микросервис для генерации изображений написания слов с **реальной AI генерацией** и **интегрированным Translation Service** для перевода русских значений в английские промпты.

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
  "num_inference_steps": 30,
  "guidance_scale": 7.5,
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
| `num_inference_steps` | integer | Количество шагов AI генерации (10-50) | `30` |
| `guidance_scale` | float | Guidance scale для AI (1.0-20.0) | `7.5` |
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

## 🆕 Translation Service Эндпоинты

### Проверка статуса Translation Service
- **URL**: `/api/translation/status`
- **Метод**: `GET`

**Ответ:**
```json
{
  "enabled": true,
  "active_model": "qwen2_7b",
  "model_loaded": true,
  "available_models": ["qwen2_7b", "qwen2_1_5b", "nllb_3_3b", "mt5_xl"],
  "statistics": {
    "total_translations": 1250,
    "cache_hits": 856,
    "cache_hit_rate": 0.685
  },
  "cache_stats": {
    "enabled": true,
    "entries": 856,
    "max_size": 10000
  }
}
```

### Переключение Translation модели
- **URL**: `/api/translation/switch-model`
- **Метод**: `POST`

**Тело запроса:**
```json
{
  "model_name": "nllb_3_3b"
}
```

### Прямой перевод (без AI генерации)
- **URL**: `/api/translation/translate`
- **Метод**: `POST`

**Тело запроса:**
```json
{
  "character": "学",
  "russian_text": "учить",
  "use_cache": true
}
```

**Ответ:**
```json
{
  "success": true,
  "translated_text": "learn, study",
  "original_text": "учить",
  "character": "学",
  "translation_time_ms": 180,
  "model_used": "Qwen/Qwen2-7B-Instruct",
  "cache_hit": false,
  "confidence_score": 0.89
}
```

## Health Check Эндпоинты (обновлено)

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

### Прогрев AI + Translation моделей
- **URL**: `/health/warmup`
- **Метод**: `POST`

**Тело запроса:**
```json
{
  "warmup_ai": true,
  "warmup_translation": true,
  "test_characters": ["学", "写", "读"]
}
```

## Примеры использования

### Генерация с автоматическим переводом (Qwen)
```bash
curl -X POST http://localhost:8600/api/writing/generate-writing-image \
  -H "Content-Type: application/json" \
  -d '{
    "word": "美丽",
    "translation": "красивый",
    "translation_model": "qwen2_7b",
    "style": "watercolor",
    "include_prompt": true
  }'
```

### Генерация с NLLB переводом
```bash
curl -X POST http://localhost:8600/api/writing/generate-writing-image \
  -H "Content-Type: application/json" \
  -d '{
    "word": "дом",
    "translation": "дом",
    "translation_model": "nllb_3_3b",
    "language": "russian"
  }'
```

### Проверка Translation Service
```bash
# Статус Translation Service
curl http://localhost:8600/api/translation/status

# Переключение модели
curl -X POST http://localhost:8600/api/translation/switch-model \
  -H "Content-Type: application/json" \
  -d '{"model_name": "mt5_xl"}'

# Прямой перевод
curl -X POST http://localhost:8600/api/translation/translate \
  -H "Content-Type: application/json" \
  -d '{
    "character": "水",
    "russian_text": "вода"
  }'
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
# writing_service/conf/config/translation.yaml
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
