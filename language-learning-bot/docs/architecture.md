# Архитектура проекта (ОБНОВЛЕНО с Translation Service)

## Общий обзор

Language Learning Bot построен на современной модульной архитектуре с четким разделением на независимые компоненты и **реальной AI системой генерации изображений с переводом**:

- **Frontend (Telegram-бот)** - взаимодействие с пользователем через Telegram API
- **Backend (REST API)** - обработка бизнес-логики и работа с базой данных
- **🔥 Writing Service (AI микросервис)** - **реальная AI генерация изображений** с Union ControlNet + **Translation Service**
- **База данных (MongoDB)** - хранение данных о языках, словах и пользователях
- **Common (Общие модули)** - утилиты, используемые несколькими компонентами

## Схема взаимодействия компонентов

```
┌─────────────────┐    HTTP/REST   ┌─────────────────┐    MongoDB      ┌─────────────────┐
│                 │    requests    │                 │    driver       │                 │
│   Frontend      │◄──────────────►│    Backend      │◄───────────────►│    MongoDB      │
│   (Telegram)    │                │    (REST API)   │                 │   (Database)    │
│                 │                │                 │                 │                 │
└─────────┬───────┘                └─────────────────┘                 └─────────────────┘
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
```
