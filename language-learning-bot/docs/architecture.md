# Архитектура проекта

## Общий обзор

Language Learning Bot построен на модульной архитектуре с четким разделением на независимые компоненты:

| Компонент | Порт | Назначение |
|-----------|------|-----------|
| **Backend (REST API)** | 8500 | Хранение данных, работа с MongoDB |
| **BLS (Business Logic Service)** | 8700 | Логика обучения, сессии, карточки, графики |
| **Web Frontend** | 8800 | Веб-интерфейс (FastAPI + Jinja2 + HTMX) |
| **Android App** | — | Нативное Android-приложение (Kotlin + Retrofit) |
| **Telegram Bot (новый)** | — | Telegram-фронтенд через BLS |
| **Telegram Bot (старый)** | — | Устаревший, не изменяется |
| **Writing Service** | — | AI-генерация изображений (отключён) |
| **MongoDB** | 27017 | База данных |

## Схема взаимодействия компонентов

```
┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐
│  Web Frontend    │  │  Telegram Bot    │  │  Android App     │
│  (порт 8800)     │  │  (новый)         │  │  (Kotlin)        │
└────────┬─────────┘  └────────┬─────────┘  └────────┬─────────┘
         │                     │                      │
         │            HTTP/REST (прямые вызовы BLS)   │
         ▼                     ▼                      ▼
┌──────────────────────────────────────────────────────────────┐
│     BLS — Business Logic Service  (порт 8700)                │
│  • Сессии изучения (session_service)                         │
│  • Построение карточек (card_builder)                        │
│  • Статистика и графики                                      │
│  • Аутентификация: /auth/mobile/create|activate              │
└────────────────────┬─────────────────────────────────────────┘
                     │  HTTP/REST
                     ▼
┌──────────────────────────────────────────┐    ┌─────────────────┐
│     Backend REST API (порт 8500)         │◄──►│    MongoDB      │
│  • Слова, языки, пользователи            │    │   (порт 27017)  │
│  • Прогресс и статистика пользователя    │    └─────────────────┘
└──────────────────────────────────────────┘
          │                                 ▲                                   ▲
          │ Telegram Bot API               │                                   │
          │                                │                         ┌─────────┴─────────┐
          │         🔥 AI IMAGE            │                         │                   │
          │         GENERATION             │                         │   Администратор   │
          ▼         HTTP/REST              ▼                         │   (Консоль)       │
┌─────────────────┐◄──────────────►┌─────────────────┐                │                   │
│                 │                │ 🔥 Writing      │                └───────────────────┘
│  Пользователь   │                │    Service      │
│    (Чат)        │                │ (AI + Translation)│              ┌─────────────────┐
│                 │                │                 │                │ 🔥 GPU Cluster  │
└─────────────────┘                └─────────┬───────┘                │                 │
                                             │                        │ • SDXL + ControlNet│
                                             │ AI + Translation       │ • Qwen/NLLB/mT5│
                                             │ Models                 │ • VRAM Pool     │
                                             ▼                        │ • Model Cache   │
                                   ┌─────────────────┐                └─────────────────┘
                                   │ 🔥 AI Pipeline  │
                                   │                 │
                                   │ • Translation   │
                                   │ • SDXL Base     │
                                   │ • Union ControlNet│
                                   │ • Prompt Builder │
                                   └─────────────────┘
```

## Android App — авторизация

Android-приложение — ещё один фронтенд, обращающийся к BLS напрямую. Не требует изменений в Backend или BLS кроме двух новых эндпоинтов аутентификации.

### Схема подключения

```
1. Пользователь открывает Telegram-бот → /connect_android
2. Бот вызывает POST /auth/mobile/create {user_id}
   BLS возвращает 6-символьный одноразовый код (TTL 10 мин)
3. Бот показывает код пользователю: ABC123
4. Пользователь вводит код в Android-приложении
5. Приложение вызывает POST /auth/mobile/activate {code}
   BLS возвращает user_id (код удаляется — single-use)
6. Приложение сохраняет user_id локально (SharedPreferences)
7. Все дальнейшие вызовы BLS используют этот user_id напрямую
```

### Новые BLS-эндпоинты

| Эндпоинт | Метод | Описание |
|----------|-------|---------|
| `/auth/mobile/create` | POST | `{user_id}` → `{code, ttl_seconds}` |
| `/auth/mobile/activate` | POST | `{code}` → `{user_id}` (single-use) |

### Структура Android-приложения (`android/`)

```
app/src/main/java/com/langbot/app/
├── LoginActivity.kt       — ввод кода, инициализация
├── LanguagesActivity.kt   — список языков
├── StudyActivity.kt       — карточка слова (основная функция)
├── StatsActivity.kt       — статистика
├── network/
│   ├── BLSService.kt      — Retrofit API-клиент
│   └── ApiModels.kt       — модели данных
└── prefs/UserPrefs.kt     — хранение user_id и BLS URL
```

## 🔥 Writing Service (AI микросервис с переводом)

**Обновленная архитектура** с интегрированной системой перевода:

### AI + Translation Архитектурные слои

```
┌─────────────────────────────────────┐
│          FastAPI Layer              │
│  • AI Generation endpoints          │
│  • Translation status & control     │
│  • Health checks with GPU stats     │
└─────────────────┬───────────────────┘
                  │
┌─────────────────┴───────────────────┐
│        AI Service Layer             │
│  • WritingImageService              │
│  • 🆕 TranslationService            │
│  • Prompt Engineering               │
└─────────────────┬───────────────────┘
                  │
┌─────────────────┴───────────────────┐
│     🆕 Translation Layer            │
│  • Russian → English conversion     │
│  • Qwen/NLLB/mT5 models            │
│  • Caching & Fallback              │
└─────────────────┬───────────────────┘
                  │
┌─────────────────┴───────────────────┐
│       AI Pipeline Layer             │
│  • AIImageGenerator (modular)       │
│  • Multi-ControlNet Pipeline        │
│  • Conditioning Generators          │
└─────────────────┬───────────────────┘
                  │
┌─────────────────┴───────────────────┐
│        AI Models Layer              │
│  • Translation Models (Qwen/NLLB)   │
│  • Stable Diffusion XL              │
│  • Union ControlNet                 │
│  • GPU Manager                      │
└─────────────────────────────────────┘
```

### 🆕 Translation Service Компоненты

#### **Translation Models:**
- **Qwen2-7B/1.5B** - приоритетные модели с отличной поддержкой CJK
- **NLLB-3.3B/1.3B** - Meta multilingual translation
- **mT5-XL/Large** - Google multilingual T5
- **OPUS-MT** - специализированные легкие модели

#### **Translation Pipeline:**
```
Русский текст → Translation Service → Английский промпт → AI Generation
```

#### **Modular AI Architecture:**
- **TranslationManager** - управление переводом
- **ModelManager** - загрузка AI моделей  
- **ConditioningManager** - conditioning генерация
- **PromptManager** - построение промптов
- **ImageProcessor** - обработка изображений

### Технологический стек AI + Translation

```
🔤 Translation Models:
├── Qwen2-7B-Instruct                   # 🎯 Приоритетная модель
├── facebook/nllb-200-3.3B              # Multilingual translation
├── google/mt5-xl                       # Text-to-text generation
└── Helsinki-NLP/opus-mt-*              # Lightweight models

🤖 AI Models:
├── Stable Diffusion XL Base 1.0        # Основная генеративная модель
├── Union ControlNet SDXL 1.0            # Единая ControlNet модель
└── VAE + Scheduler                      # Оптимизации

📚 Frameworks:
├── Transformers >= 4.39.0              # Translation models
├── Diffusers >= 0.25.0                 # AI generation
├── SentencePiece >= 0.1.99             # NLLB tokenization
└── PyTorch >= 2.1.0                    # ML framework
```

## 🆕 Translation Workflow

### Новый процесс генерации:

```
1. Character Input: "学"
2. Russian Translation: "учить"
3. 🆕 Translation Service: "учить" → "learn, study"
4. Prompt Building: "A illustration of learning/study inspired by 学"
5. AI Generation: SDXL + Union ControlNet
6. Result: AI изображение с качественным английским промптом
```

### Memory Requirements (обновлено):

```
80GB VRAM: SDXL(6GB) + ControlNet(2GB) + Qwen2-7B(14GB) = ~22GB
40GB VRAM: SDXL(6GB) + ControlNet(2GB) + NLLB-3.3B(7GB) = ~15GB  
24GB VRAM: SDXL(6GB) + ControlNet(2GB) + mT5-Large(3GB) = ~11GB
```

## База данных MongoDB

### Коллекции (обновлено):

| Коллекция | Назначение | 🆕 Translation Integration |
|-----------|------------|---------------------------|
| `languages` | Языки для изучения | Поддержка translation для всех языков |
| `words` | Слова с переводами | Исходные данные для translation |
| `users` | Пользователи системы | Translation preferences |
| `user_statistics` | Статистика изучения | **Translation stats** |
| **🆕 `translation_cache`** | **Новая коллекция** | **Кэш переводов** |
| **🆕 `ai_generation_logs`** | **Обновлена** | **AI + Translation логи** |

## 🆕 Translation + AI генерация workflow

```
┌─────────────┐  Translation  ┌─────────────┐   AI API    ┌─────────────┐
│  Frontend   │──────────────►│   Backend   │─────────────►│ Writing     │
│             │   RU text    │             │  EN prompt  │ Service     │
│ User Input  │              │ API Forward │             │ (AI+Trans)  │
└─────────────┘              └─────────────┘             └──────┬──────┘
       ▲                            │                           │
       │                            │                           │ Pipeline
       │   AI Image + Translation   │   Response                ▼
       │                            ▼               ┌─────────────────┐
┌─────────────┐               ┌─────────────┐      │ Translation     │
│  Enhanced   │◄──────────────│  AI + Trans │      │ • Cache         │
│  Interface  │               │   Result    │      │ • Qwen/NLLB     │
│ with Meta   │               │             │      │ • Fallback      │
└─────────────┘               └─────────────┘      └─────────┬───────┘
                                                             │
                                                             ▼
                                                   ┌─────────────────┐
                                                   │ AI Generation   │
                                                   │ • SDXL          │
                                                   │ • ControlNet    │
                                                   │ • Conditioning  │
                                                   └─────────────────┘

## BLS — card_builder и session_service

### Жизненный цикл карточки слова

```
show_answer=False           show_answer=True (score_changed=False)   show_answer=True (score_changed=True)
─────────────────           ──────────────────────────────────────   ──────────────────────────────────────
Показать слово              Пользователь нажал "Не знаю"             Пользователь нажал "Знаю"
Кнопки: Знаю | Не знаю     score=0, interval сброшен               score=1, interval увеличен
         | Пропускать        Кнопки: Дальше | Пропускать             Кнопки: К следующему | Ой не знаю
                                                                              | Пропускать
```

### Бейдж (score_badge) — отображение предыдущего состояния

После того как пользователь нажимает "Знаю" или "Показать ответ", слово в БД обновляется **до** отрисовки карточки. Чтобы бейдж показывал **состояние до ответа** (а не новое), `session_service` сохраняет старые значения в сессию перед обновлением:

```python
session["prev_score"] = uwd.get("score", -1)
session["prev_interval"] = uwd.get("check_interval", 0)
session["prev_next_check_date"] = uwd.get("next_check_date", "")
```

`card_builder` использует `prev_*` значения для `score_badge` когда `show_answer=True`:
- Бейдж: "✓ знал · 4д · след. 2026-01-01" — старый интервал
- Notice в карточке: "✅ Следующий интервал: 8 дн." — новый интервал

### Ключевые файлы BLS

| Файл | Назначение |
|------|-----------|
| `business_logic_service/app/services/card_builder.py` | Сборка карточки: контент, кнопки, бейдж |
| `business_logic_service/app/services/session_service.py` | Управление сессией: know_word, show_answer_word, rate_word |
| `business_logic_service/app/services/statistics_service.py` | Статистика и генерация графиков (кэш TTL=60s) |
```
