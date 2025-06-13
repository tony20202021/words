# Архитектура проекта (ОБНОВЛЕНО с реальной AI системой)

## Содержание

1. [Общий обзор](#общий-обзор)
2. [Схема взаимодействия компонентов](#схема-взаимодействия-компонентов)
3. [Frontend (Telegram-бот)](#frontend-telegram-бот)
4. [Backend (REST API)](#backend-rest-api)
5. [🔥 Writing Service (AI микросервис)](#writing-service-ai-микросервис)
6. [🔥 AI Pipeline архитектура](#ai-pipeline-архитектура)
7. [База данных MongoDB](#база-данных-mongodb)
8. [Потоки данных](#потоки-данных)
9. [🔥 AI генерация workflow](#ai-генерация-workflow)

## Общий обзор

Language Learning Bot построен на современной модульной архитектуре с четким разделением на независимые компоненты и **реальной AI системой генерации изображений**:

- **Frontend (Telegram-бот)** - взаимодействие с пользователем через Telegram API
- **Backend (REST API)** - обработка бизнес-логики и работа с базой данных
- **🔥 Writing Service (AI микросервис)** - **реальная AI генерация изображений** с Union ControlNet
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
│    (Чат)        │                │ (AI Generation) │                ┌─────────────────┐
│                 │                │                 │                │ 🔥 GPU Cluster  │
└─────────────────┘                └─────────┬───────┘                │                 │
                                             │                        │ • CUDA Cores   │
                                             │ AI Models              │ • Tensor Cores  │
                                             │ GPU Memory             │ • VRAM Pool     │
                                             ▼                        │ • Model Cache   │
                                   ┌─────────────────┐                └─────────────────┘
                                   │ 🔥 AI Pipeline  │
                                   │                 │
                                   │ • SDXL Base     │
                                   │ • Union ControlNet│
                                   │ • Conditioning   │
                                   │ • Prompt Builder │
                                   └─────────────────┘
```

## Frontend (Telegram-бот)

Frontend отвечает за взаимодействие с пользователями через Telegram и **интеграцию с реальной AI системой**:

### Архитектурные слои

```
┌─────────────────────────────────────┐
│           Telegram API              │
└─────────────────┬───────────────────┘
                  │
┌─────────────────┴───────────────────┐
│          Bot Layer                  │
│  • Обработка событий                │
│  • Middleware                       │
│  • FSM состояния                    │
└─────────────────┬───────────────────┘
                  │
┌─────────────────┴───────────────────┐
│        Handlers Layer               │
│  • User handlers                    │
│  • Admin handlers                   │
│  • Study handlers                   │
│  • 🔥 AI Image handlers              │
└─────────────────┬───────────────────┘
                  │
┌─────────────────┴───────────────────┐
│       Business Logic Layer          │
│  • API Client                       │
│  • 🔥 AI Integration                 │
│  • State management                 │
│  • Utils                            │
└─────────────────────────────────────┘
```

### Ключевые компоненты

- **Bot** - основной класс бота с конфигурацией
- **Handlers** - модульная система обработчиков событий с **AI интеграцией**
- **🔥 AI Handlers** - специализированные обработчики для AI генерации
- **Middleware** - промежуточное ПО для аутентификации и авторизации
- **States** - управление состояниями FSM
- **🔥 AI API Client** - интеграция с Writing Service для **реальной AI генерации**
- **Utils** - вспомогательные утилиты включая **AI утилиты**

### Технологический стек

- **aiogram 3.x** - фреймворк для Telegram ботов
- **Hydra** - управление конфигурацией
- **Pillow** - генерация изображений
- **FFmpeg** - обработка аудио
- **🔥 aiohttp** - асинхронные HTTP запросы к AI сервису

## Backend (REST API)

Backend предоставляет REST API и построен по принципам чистой архитектуры:

### Архитектурные слои

```
┌─────────────────────────────────────┐
│           API Layer                 │
│  • Routes                           │
│  • Request/Response handling        │
│  • Validation                       │
└─────────────────┬───────────────────┘
                  │
┌─────────────────┴───────────────────┐
│        Business Layer               │
│  • Services                         │
│  • Business logic                   │
│  • Domain rules                     │
└─────────────────┬───────────────────┘
                  │
┌─────────────────┴───────────────────┐
│         Data Layer                  │
│  • Repositories                     │
│  • Database access                  │
│  • Data models                      │
└─────────────────────────────────────┘
```

### Компоненты Backend

1. **Routes** - определение HTTP эндпоинтов
2. **Services** - бизнес-логика приложения
3. **Repositories** - доступ к данным
4. **Schemas** - валидация и сериализация данных

### Технологический стек

- **FastAPI** - асинхронный веб-фреймворк
- **Motor** - асинхронный драйвер MongoDB
- **Pydantic** - валидация данных
- **Hydra** - управление конфигурацией

## 🔥 Writing Service (AI микросервис)

**Новый компонент архитектуры** - полноценный AI микросервис для **реальной генерации изображений**:

### AI Архитектурные слои

```
┌─────────────────────────────────────┐
│          FastAPI Layer              │
│  • AI Generation endpoints          │
│  • Health checks with GPU stats     │
│  • Request validation               │
└─────────────────┬───────────────────┘
                  │
┌─────────────────┴───────────────────┐
│        AI Service Layer             │
│  • WritingImageService              │
│  • Prompt Engineering               │
│  • Generation orchestration         │
└─────────────────┬───────────────────┘
                  │
┌─────────────────┴───────────────────┐
│       AI Pipeline Layer             │
│  • AIImageGenerator                 │
│  • Multi-ControlNet Pipeline        │
│  • Conditioning Generators          │
└─────────────────┬───────────────────┘
                  │
┌─────────────────┴───────────────────┐
│        AI Models Layer              │
│  • Stable Diffusion XL              │
│  • Union ControlNet                 │
│  • Model Loader & GPU Manager       │
└─────────────────────────────────────┘
```

### 🔥 AI Компоненты

#### 1. **AI Image Generator** (`ai_image_generator.py`)
Основной orchestrator AI pipeline:
#### 2. **Multi-ControlNet Pipeline** (`multi_controlnet_pipeline.py`)
Union ControlNet integration с Stable Diffusion XL:
#### 3. **Conditioning Generators**
Специализированные генераторы для каждого типа conditioning:

- **Canny Conditioning** (`canny_conditioning.py`) - edge detection
- **Depth Conditioning** (`depth_conditioning.py`) - depth estimation  
- **Segmentation Conditioning** (`segmentation_conditioning.py`) - image segmentation
- **Scribble Conditioning** (`scribble_conditioning.py`) - artistic sketches

#### 4. **Model Management**
- **Model Loader** (`model_loader.py`) - загрузка AI моделей
- **GPU Manager** (`gpu_manager.py`) - управление GPU ресурсами
- **Model Cache** - кэширование загруженных моделей

### Технологический стек AI

```
🤖 AI Models:
├── Stable Diffusion XL Base 1.0        # Основная генеративная модель
├── Union ControlNet SDXL 1.0            # 🔥 Единая ControlNet модель
├── VAE (madebyollin/sdxl-vae-fp16-fix)  # Оптимизированный VAE
└── EulerAncestralDiscreteScheduler      # Scheduler для генерации

📚 AI Frameworks:
├── Diffusers >= 0.25.0                 # HuggingFace Diffusers
├── Transformers >= 4.39.0              # HuggingFace Transformers
├── Accelerate >= 0.24.0                # Ускорение инференса
├── XFormers >= 0.0.22                  # Attention optimization
├── ControlNet-Aux >= 0.0.10            # ControlNet utilities
└── PyTorch >= 2.1.0                    # Основной ML framework

🔧 Infrastructure:
├── CUDA 11.8+                          # GPU computation
├── FastAPI                             # Web framework
├── Hydra                               # Configuration management
├── Pydantic                            # Data validation
└── AsyncIO                             # Asynchronous processing
```

## 🔥 AI Pipeline архитектура

### Компоненты AI Pipeline:

#### 1. **Preprocessing Stage**
```python
async def _preprocess_character(self, character: str) -> Image.Image:
    """Рендеринг иероглифа в базовое изображение"""
    # Использует FontManager для автоподбора шрифта
```

#### 2. **Conditioning Stage**
```python
async def _generate_all_conditioning(self, base_image: Image.Image) -> Dict:
    """Параллельная генерация всех типов conditioning"""
    # Canny: edge detection для структуры
    # Depth: depth estimation для объемности
    # Segmentation: сегментация для цветов
    # Scribble: artistic sketches для стилизации
```

#### 3. **Prompt Engineering Stage**
```python
async def _generate_prompt(self, character: str, translation: str) -> str:
    """Intelligent prompt building"""
    # Style-aware templates
```

#### 4. **AI Generation Stage**
```python
async def _run_ai_generation(self, prompt: str, controls: Dict) -> Image.Image:
    """Union ControlNet + Stable Diffusion XL generation"""
    # Union ControlNet conditioning
    # Memory-efficient generation
```

## База данных MongoDB

MongoDB используется как основное хранилище данных с следующей структурой:

### Коллекции

| Коллекция | Назначение | 🔥 AI Integration |
|-----------|------------|-------------------|
| `languages` | Языки для изучения | Поддержка AI генерации для всех языков |
| `words` | Слова с переводами | Входные данные для AI генерации |
| `users` | Пользователи системы | Настройки AI генерации |
| `user_statistics` | Статистика изучения | **🔥 Статистика AI генерации** |
| `user_language_settings` | Настройки по языкам | **🔥 AI настройки пользователей** |
| **🔥 `ai_generation_logs`** | **Новая коллекция** | **Логи AI генерации** |
| **🔥 `ai_cache`** | **Новая коллекция** | **Кэш AI результатов** |

## Потоки данных

### 🔥 Поток AI генерации изображений

```
┌─────────────┐    HTTP     ┌─────────────┐    AI API   ┌─────────────┐
│  Frontend   │─────────────►│   Backend   │─────────────►│ Writing     │
│             │    Request  │             │   Forward   │ Service     │
│ User Action │             │ API Service │             │ (AI)        │
└─────────────┘             └─────────────┘             └──────┬──────┘
       ▲                           │                           │
       │                           │                           │ AI Pipeline
       │    AI Image               │    Response               ▼
       │                           ▼                   ┌─────────────┐
┌─────────────┐              ┌─────────────┐          │ GPU Cluster │
│  Updated    │◄─────────────│  Processed  │          │             │
│  Interface  │              │   AI Data   │          │ • SDXL      │
│ with Image  │              │             │          │ • Union CN  │
└─────────────┘              └─────────────┘          │ • Memory    │
                                                      │ • Cache     │
                                                      └─────────────┘
```

### Традиционный поток изучения слов

```
┌─────────────┐    HTTP     ┌─────────────┐    Query    ┌─────────────┐
│  Frontend   │─────────────►│   Backend   │─────────────►│  MongoDB    │
│             │    Request  │             │             │             │
│ User Action │             │ API Service │             │ Collection  │
└─────────────┘             └─────────────┘             └─────────────┘
       ▲                           │                           │
       │                           │                           │
       │    Response               │    Data                   │
       │                           ▼                           ▼
┌─────────────┐              ┌─────────────┐              ┌─────────────┐
│  Updated    │◄─────────────│  Processed  │◄─────────────│  Retrieved  │
│  Interface  │              │    Data     │              │    Data     │
└─────────────┘              └─────────────┘              └─────────────┘
```
