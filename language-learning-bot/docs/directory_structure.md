# Структура каталогов и файлов проекта (ОБНОВЛЕНО с AI)

## Корневой каталог

```
language-learning-bot/
├── README.md
├── .gitignore
├── requirements.txt
├── requirements_cpu.txt                  # Базовые зависимости  
├── requirements_gpu.txt                  # 🔥 AI зависимости для GPU
├── environment.yml                       # Базовое окружение
├── environment_gpu.yml                   # 🔥 AI окружение с GPU поддержкой
├── docker-compose.yml
├── .env.example
├── .env
├── pyproject.toml
├── setup.py
├── start_1_db.sh
├── start_2_backend.sh
├── start_3_frontend.sh
├── start_4_writing_service.sh            # 🔥 Запуск AI сервиса
├── start_3_frontend_auto_reload.sh
├── setup_watchdog.sh
├── run_export_env.sh
├── run_tests.sh
├── .backend.pid
├── .frontend.pid
├── .writing_service.pid                  # 🔥 PID файл AI сервиса
├── docs/
├── frontend/
├── backend/
├── writing_service/                      # 🔥 AI микросервис генерации
├── common/
└── scripts/
```

## Каталог документации

```
docs/
├── README.md
├── summary.md
├── architecture.md                       # 🔥 ОБНОВЛЕН: реальная AI архитектура
├── project_description.md                # 🔥 ОБНОВЛЕН: реальные AI возможности  
├── backlog.md
│
├── user/
│   ├── quick_start.md
│   ├── commands.md
│   └── learning_guide.md
│
├── installation/
│   ├── installation_guide.md             # 🔥 ОБНОВЛЕН: реальные AI зависимости
│   ├── environment_setup.md              # 🔥 ОБНОВЛЕН: реальные GPU настройки
│   ├── mongodb_setup.md
│   └── gpu_requirements.md               # 🔥 НОВЫЙ: требования к GPU
│
├── running/
│   ├── running_guide.md                  # 🔥 ОБНОВЛЕН: реальный Writing Service
│   ├── scripts_reference.md
│   ├── auto_reload.md
│   ├── deployment_guide.md
│   ├── ai_performance_tuning.md          # 🔥 НОВЫЙ: настройка AI производительности
│   └── ai_monitoring.md                  # 🔥 НОВЫЙ: мониторинг AI компонентов
│
├── api/
│   ├── api_reference.md
│   ├── backend_api.md
│   ├── writing_service_api.md             # 🔥 ОБНОВЛЕН: реальные AI API
│   └── ai_generation_endpoints.md        # 🔥 НОВЫЙ: детальная AI API документация
│
├── development/
│   ├── testing_guide.md
│   ├── bot_test_framework.md
│   ├── configuration.md
│   ├── directory_structure.md            # 🔥 ЭТОТ ФАЙЛ - обновленная структура
│   ├── router_organization.md
│   ├── show_big.md
│   ├── meta_states_guide.md
│   ├── ai_development_guide.md           # 🔥 НОВЫЙ: разработка AI компонентов
│   ├── controlnet_union_guide.md         # 🔥 НОВЫЙ: работа с Union ControlNet
│   ├── gpu_optimization.md               # 🔥 НОВЫЙ: оптимизация GPU
│   ├── ai_troubleshooting.md             # 🔥 НОВЫЙ: устранение проблем AI
│   ├── ai_testing_guide.md               # 🔥 НОВЫЙ: тестирование AI компонентов
│   └── model_management.md               # 🔥 НОВЫЙ: управление AI моделями
│
└── functionality/
    ├── bot_commands.md
    ├── admin_tools.md
    ├── learning_system.md                # 🔥 ОБНОВЛЕН: реальная AI интеграция
    └── ai_image_generation.md            # 🔥 ПОЛНОСТЬЮ ОБНОВЛЕН: реальная AI система
```

## Общие модули (Common)

```
common/
├── __init__.py
├── utils/
│   ├── __init__.py
│   ├── font_utils.py                    # 🔥 ОБНОВЛЕН: FontManager для AI рендеринга
│   └── logger.py                        # 🔥 ОБНОВЛЕН: поддержка AI логирования
└── tests/
    ├── __init__.py
    ├── conftest.py
    ├── test_utils_logger.py
    └── test_font_utils.py               # 🔥 ОБНОВЛЕН: тесты FontManager для AI
```



# Структура каталогов и файлов проекта (ОБНОВЛЕНО с Translation Service + Модульная архитектура)

## 🔥 Writing Service (Реальный AI микросервис с переводом)

```
writing_service/
├── app/
│   ├── __init__.py
│   ├── main_writing_service.py           # 🔥 РЕАЛЬНАЯ AI + Translation инициализация
│   ├── api/
│   │   ├── __init__.py
│   │   └── routes/
│   │       ├── __init__.py
│   │       ├── models/
│   │       │   ├── __init__.py
│   │       │   ├── requests.py           # 🔥 AI + Translation запросы
│   │       │   └── responses.py          # 🔥 AI + Translation ответы
│   │       ├── services/
│   │       │   ├── __init__.py
│   │       │   ├── writing_image_service.py  # 🔥 AI + Translation интеграция
│   │       │   └── validation_service.py
│   │       ├── writing_images.py         # 🔥 AI + Translation эндпоинты
│   │       └── health.py                 # 🔥 AI + Translation health checks
│   ├── ai/                               # 🔥 РЕАЛЬНЫЕ AI компоненты
│   │   ├── __init__.py
│   │   ├── ai_image_generator.py         # 🔥 РЕФАКТОРИНГ: основной orchestrator
│   │   ├── multi_controlnet_pipeline.py  # 🔥 Union ControlNet Pipeline
│   │   ├── 🆕 core/                      # 🆕 МОДУЛЬНАЯ АРХИТЕКТУРА
│   │   │   ├── __init__.py
│   │   │   ├── generation_config.py     # 🆕 Конфигурация AI
│   │   │   ├── generation_result.py     # 🆕 Результаты генерации
│   │   │   ├── model_manager.py         # 🆕 Управление AI моделями
│   │   │   ├── conditioning_manager.py  # 🆕 Conditioning генерация
│   │   │   ├── translation_manager.py   # 🆕 Translation Service интеграция
│   │   │   ├── prompt_manager.py        # 🆕 Prompt building
│   │   │   └── image_processor.py       # 🆕 Обработка изображений
│   │   ├── 🆕 services/                  # 🆕 TRANSLATION SERVICE
│   │   │   ├── __init__.py
│   │   │   └── translation_service.py   # 🆕 РЕАЛЬНЫЙ Translation Service
│   │   ├── conditioning/                 # 🔥 РЕАЛЬНЫЕ Conditioning генераторы
│   │   │   ├── __init__.py
│   │   │   ├── base_conditioning.py
│   │   │   ├── canny_conditioning.py    # 🔥 Canny edge detection
│   │   │   ├── depth_conditioning.py    # 🔥 Depth estimation
│   │   │   ├── segmentation_conditioning.py # 🔥 Сегментация
│   │   │   └── scribble_conditioning.py # 🔥 Scribble generation
│   │   ├── prompt/                       # 🔥 РЕАЛЬНЫЙ Prompt engineering
│   │   │   ├── __init__.py
│   │   │   ├── prompt_builder.py        # 🔥 РЕАЛЬНЫЙ построитель промптов
│   │   │   └── style_definitions.py     # 🔥 РЕАЛЬНЫЕ стилевые определения
│   │   ├── models/                       # 🔥 РЕАЛЬНЫЕ AI + Translation модели
│   │   │   ├── __init__.py
│   │   │   ├── model_loader.py          # 🔥 AI модели загрузка
│   │   │   ├── gpu_manager.py           # 🔥 GPU управление
│   │   │   ├── translation_model.py     # 🆕 РЕАЛЬНЫЕ Translation модели
│   │   │   └── controlnet_union.py      # 🔥 Union ControlNet модель
│   │   └── pipeline/                     # 🔥 РЕАЛЬНЫЕ AI Pipeline компоненты
│   │       ├── __init__.py
│   │       ├── pipeline_controlnet_union_sd_xl.py  # 🔥 Union ControlNet Pipeline
│   │       └── pipeline_utils.py
│   └── utils/
│       ├── __init__.py
│       ├── config_holder.py
│       ├── image_utils.py               # 🔥 РЕАЛЬНЫЙ ImageProcessor
│       └── logger.py
├── conf/
│   ├── __init__.py
│   └── config/
│       ├── __init__.py
│       ├── default.yaml                 # 🆕 ОБНОВЛЕН: подключает translation.yaml
│       ├── api.yaml
│       ├── generation.yaml
│       ├── ai_generation.yaml           # 🔥 AI генерация (без translation)
│       ├── 🆕 translation.yaml          # 🆕 ОТДЕЛЬНАЯ Translation конфигурация
│       └── logging.yaml
├── requirements_cpu.txt
├── requirements_gpu.txt                 # 🆕 ОБНОВЛЕН: Translation зависимости
├── environment.yml
├── environment_gpu.yml                  # 🆕 ОБНОВЛЕН: Translation environment
├── cache/                               # 🔥 РЕАЛЬНЫЕ AI + Translation кэши
│   ├── huggingface/                     # HuggingFace модели
│   │   ├── models--stabilityai--stable-diffusion-xl-base-1.0/
│   │   ├── models--xinsir--controlnet-union-sdxl-1.0/
│   │   ├── 🆕 models--Qwen--Qwen2-7B-Instruct/           # 🆕 Qwen модели
│   │   ├── 🆕 models--facebook--nllb-200-3.3B/           # 🆕 NLLB модели
│   │   └── 🆕 models--google--mt5-xl/                    # 🆕 mT5 модели
│   ├── transformers/                    # Transformers кэш
│   ├── torch/                           # PyTorch кэш
│   ├── 🆕 translation_cache.json        # 🆕 Кэш переводов
│   └── pytorch_kernel_cache/            # Compiled CUDA kernels
└── tests/
    ├── __init__.py
    ├── conftest.py
    ├── test_health.py
    ├── test_writing_images.py
    ├── test_ai/                          # 🔥 РЕАЛЬНЫЕ AI тесты
    │   ├── __init__.py
    │   ├── test_ai_image_generator.py
    │   ├── test_multi_controlnet.py
    │   ├── 🆕 test_core/                 # 🆕 Тесты модульной архитектуры
    │   │   ├── test_translation_manager.py  # 🆕 Тесты Translation Manager
    │   │   ├── test_model_manager.py        # 🆕 Тесты Model Manager
    │   │   ├── test_conditioning_manager.py # 🆕 Тесты Conditioning Manager
    │   │   ├── test_prompt_manager.py       # 🆕 Тесты Prompt Manager
    │   │   └── test_image_processor.py      # 🆕 Тесты Image Processor
    │   ├── 🆕 test_services/             # 🆕 Тесты Translation Service
    │   │   ├── test_translation_service.py  # 🆕 РЕАЛЬНЫЕ тесты перевода
    │   │   └── test_translation_models.py   # 🆕 Тесты Translation Models
    │   ├── test_conditioning/
    │   │   ├── test_canny_conditioning.py
    │   │   ├── test_depth_conditioning.py
    │   │   ├── test_segmentation_conditioning.py
    │   │   └── test_scribble_conditioning.py
    │   ├── test_prompt/
    │   │   ├── test_prompt_builder.py
    │   │   └── test_style_definitions.py
    │   └── test_models/
    │       ├── test_model_loader.py
    │       ├── test_gpu_manager.py
    │       └── 🆕 test_translation_model.py  # 🆕 Тесты Translation Models
    ├── integration/
    │   ├── __init__.py
    │   ├── test_full_ai_pipeline.py
    │   ├── 🆕 test_translation_pipeline.py   # 🆕 Интеграционные тесты перевода
    │   └── test_gpu_scenarios.py
    └── benchmarks/
        ├── __init__.py
        ├── performance_suite.py
        ├── 🆕 translation_benchmarks.py     # 🆕 Бенчмарки Translation Service
        └── memory_profiling.py
```

## Фронтенд (Telegram-бот)

```
frontend/
├── app/
│   ├── __init__.py
│   ├── main_frontend.py
│   ├── api/
│   │   ├── __init__.py
│   │   ├── client.py                     # 🆕 ОБНОВЛЕН: Translation Service интеграция
│   │   └── models/
│   │       ├── __init__.py
│   │       ├── language.py
│   │       ├── user.py
│   │       ├── word.py
│   │       └── 🆕 ai_models.py           # 🆕 AI + Translation модели
│   ├── handlers/
│   │   ├── admin/
│   │   │   ├── __init__.py
│   │   │   ├── admin_basic_handlers.py
│   │   │   ├── admin_language_handlers.py
│   │   │   ├── admin_upload_handlers.py
│   │   │   ├── admin_word_handlers.py
│   │   │   └── 🆕 admin_ai_handlers.py   # 🆕 AI + Translation администрирование
│   │   ├── user/
│   │   │   ├── __init__.py
│   │   │   ├── basic_handlers.py
│   │   │   ├── help_handlers.py
│   │   │   ├── hint_handlers.py
│   │   │   ├── settings_handlers.py
│   │   │   ├── stats_handlers.py
│   │   │   └── 🆕 ai_image_handlers.py   # 🆕 AI + Translation для пользователей
│   │   └── study/
│   │       ├── __init__.py
│   │       ├── study_commands.py
│   │       ├── study_words.py
│   │       ├── study_word_actions.py
│   │       ├── study_hint_handlers.py
│   │       └── 🆕 ai_writing_handlers.py # 🆕 AI + Translation в изучении
│   └── utils/
│       ├── __init__.py
│       ├── admin_utils.py
│       ├── api_utils.py
│       ├── big_word_generator.py
│       └── 🆕 ai_utils.py                # 🆕 AI + Translation утилиты
├── conf/
│   ├── __init__.py
│   └── config/
│       ├── __init__.py
│       ├── default.yaml
│       ├── bot.yaml
│       ├── api.yaml                      # 🆕 ОБНОВЛЕН: Writing Service + Translation URL
│       ├── logging.yaml
│       ├── learning.yaml
│       └── 🆕 ai.yaml                    # 🆕 AI + Translation настройки frontend
└── tests/
    ├── test_handlers/
    │   ├── test_admin/
    │   │   └── 🆕 test_admin_ai_handlers.py  # 🆕 Тесты AI администрирования
    │   ├── test_user/
    │   │   └── 🆕 test_ai_image_handlers.py  # 🆕 Тесты AI изображений
    │   └── test_study/
    │       └── 🆕 test_ai_writing_handlers.py # 🆕 Тесты AI в изучении
    ├── test_utils/
    │   └── 🆕 test_ai_utils.py              # 🆕 Тесты AI утилит
    └── test_api/
        ├── test_client.py               # 🆕 ОБНОВЛЕН: Translation Service тесты
        └── 🆕 test_ai_integration.py    # 🆕 Интеграционные AI + Translation тесты
```

## Служебные скрипты

```
scripts/
├── __init__.py
├── init_db.py
├── seed_data.py
├── run_tests.py
├── migrate_data.py
├── admin_manager.py
├── 🆕 ai_model_downloader.py            # 🆕 Загрузка AI + Translation моделей
├── 🆕 translation_model_downloader.py   # 🆕 Специально для Translation моделей
├── 🆕 gpu_benchmark.py                  # 🆕 Бенчмарк GPU
├── 🆕 ai_warmup.py                      # 🆕 Прогрев AI + Translation моделей
├── 🆕 translation_cache_manager.py      # 🆕 Управление кэшем переводов
└── 🆕 ai_cache_cleaner.py               # 🆕 Очистка AI кэшей
```
