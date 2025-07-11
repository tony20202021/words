# Описание проекта Language Learning Bot (ОБНОВЛЕНО с AI)

## Назначение и цели проекта

Language Learning Bot - комплексная система для эффективного изучения иностранных слов с **реальной AI генерацией изображений**. Проект решает задачи:

- Структурированное изучение иностранных слов
- Автоматизация интервального повторения
- Персональные подсказки пользователей
- **🔥 Реальная AI генерация изображений написания** с Union ControlNet
- Отслеживание прогресса изучения
- Административный интерфейс управления

## Архитектура системы

Микросервисная архитектура из четырех основных компонентов:

### 1. MongoDB (База данных)
- Хранение языков, слов, пользователей
- Статистика изучения и настройки
- **🔥 Логи AI генерации и кэш**
- Порт: 27017

### 2. Backend API (Основной сервер)
- REST API управления данными
- Бизнес-логика изучения
- Интеграция с базой данных
- Порт: 8500

### 3. 🔥 Writing Service (AI микросервис)
- **Реальная AI генерация изображений** 
- **Stable Diffusion XL + Union ControlNet**
- Multi-conditioning (canny, depth, segmentation, scribble)
- GPU оптимизация и memory management
- Порт: 8600

### 4. Frontend (Telegram-бот)
- Интерфейс пользователя
- **Интеграция с реальной AI генерацией**
- Система состояний и обработчиков

## Режимы работы

1. **Режим пользователя** - изучение языков с **AI изображениями**
2. **Режим администратора** - управление системой и **мониторинг AI**

## Функциональность пользователя

### Изучение слов
- Интервальное повторение
- **🔥 Реальная AI генерация изображений написания**
- Система подсказок (фонетика, ассоциации, значение, написание)
- Оценка знаний и прогресс

### 🔥 AI генерация изображений
- **4 типа conditioning** (canny, depth, segmentation, scribble)
- **GPU оптимизация** под разные карты (12GB-80GB)

### Персонализация
- Настройки для каждого языка
- Управление подсказками

## Функциональность администратора

### Управление контентом
- Создание/редактирование языков
- Загрузка списков слов
- Поиск по частотным спискам

### 🔥 AI мониторинг
- **Статус AI моделей и GPU**
- **Performance метрики генерации**
- **Memory usage и optimization**
- **Health checks AI компонентов**

### Аналитика
- Статистика пользователей

## Технический стек

### Основные технологии
- **Python 3.8+** - язык программирования
- **Telegram Bot API** - платформа взаимодействия
- **MongoDB** - база данных
- **FastAPI** - backend API
- **Aiogram 3.x** - frontend framework

### 🔥 AI технологии
```
AI Models:
├── Stable Diffusion XL Base 1.0      # Основная модель
├── Union ControlNet SDXL 1.0          # ControlNet модель
└── Optimized VAE & Scheduler          # Оптимизации

AI Frameworks:
├── Diffusers >= 0.25.0               # HuggingFace
├── Transformers >= 4.39.0            # HuggingFace  
├── PyTorch >= 2.1.0                  # ML framework
├── XFormers >= 0.0.22                # Optimization
└── CUDA 11.8+                        # GPU support
```

## База данных

### Основные коллекции
- **languages** - доступные языки
- **words** - слова с переводами
- **users** - пользователи системы
- **user_statistics** - статистика изучения + **AI генерация**
- **user_language_settings** - настройки + **AI preferences**

### 🔥 Новые AI коллекции
- **ai_generation_logs** - логи AI генерации
- **ai_cache** - кэш результатов AI

## 🔥 Writing Service API

### AI Generation эндпоинты
- `POST /api/writing/generate-writing-image` - **реальная AI генерация**
- `POST /api/writing/generate-writing-image-binary` - бинарный формат
- `GET /api/writing/status` - статус AI системы

### Health Check эндпоинты  
- `GET /health` - базовая проверка
- `GET /health/detailed` - **детальная AI диагностика**
- `GET /health/ready` - готовность AI моделей
- `POST /health/warmup` - **прогрев AI моделей**

### 🔥 AI возможности
- **GPU optimization** - 12GB-80GB VRAM
- **Lazy loading** - модели загружаются при первом запросе

## Взаимодействие компонентов

```
Frontend ↔ Backend: Основные данные (языки, слова, пользователи)
Frontend ↔ Writing Service: AI генерация изображений
Backend ↔ MongoDB: Хранение всех данных
Writing Service ↔ GPU: Реальная AI обработка
```

## Сценарии использования

### 🔥 AI-powered изучение слов
1. Пользователь выбирает язык
2. Система показывает слово
3. **Запрос к AI сервису для генерации изображения**
4. **Реальная AI генерация через Union ControlNet**
5. Пользователь изучает с AI изображением
6. Оценка и планирование повторения

### Создание подсказок с AI
1. Пользователь видит слово
2. **Просматривает AI изображение написания**
3. Создает персональную подсказку
4. Система сохраняет с **AI метаданными**

### 🔥 Административное управление AI
1. **Мониторинг статуса AI моделей**
2. **Проверка GPU memory usage**
3. **Анализ performance метрик**
4. **Управление AI cache и оптимизациями**

## Performance характеристики

### 🔥 AI Generation метрики
```
Timing:
├── Cold start: ~15-30s (model loading)
├── Warm generation: ~8-12s (RTX 4090)
└── Cache hit: <1s

Memory:
├── Models: ~6-8GB VRAM
├── Generation: +2-4GB peak
└── Optimization: auto-scaling по GPU
```
