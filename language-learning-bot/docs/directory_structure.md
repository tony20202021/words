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

## 🔥 Writing Service (Реальный AI микросервис генерации)

```
writing_service/
├── app/
│   ├── __init__.py
│   ├── main_writing_service.py           # 🔥 РЕАЛЬНАЯ AI инициализация
│   ├── api/
│   │   ├── __init__.py
│   │   └── routes/
│   │       ├── __init__.py
│   │       ├── models/
│   │       │   ├── __init__.py
│   │       │   ├── requests.py           # 🔥 Реальные AI запросы
│   │       │   └── responses.py          # 🔥 Реальные AI ответы с метаданными
│   │       ├── services/
│   │       │   ├── __init__.py
│   │       │   ├── writing_image_service.py  # 🔥 РЕАЛЬНАЯ AI интеграция
│   │       │   └── validation_service.py     # 🔥 Универсальная валидация
│   │       ├── writing_images.py         # 🔥 РЕАЛЬНАЯ AI генерация эндпоинты
│   │       └── health.py                 # 🔥 AI health checks с GPU мониторингом
│   ├── ai/                               # 🔥 РЕАЛЬНЫЕ AI компоненты
│   │   ├── __init__.py
│   │   ├── ai_image_generator.py         # 🔥 ОСНОВНОЙ AI ГЕНЕРАТОР (РЕАЛЬНЫЙ)
│   │   ├── multi_controlnet_pipeline.py  # 🔥 Union ControlNet Pipeline (РЕАЛЬНЫЙ)
│   │   ├── conditioning/                 # 🔥 РЕАЛЬНЫЕ Conditioning генераторы
│   │   │   ├── __init__.py
│   │   │   ├── base_conditioning.py     # 🔥 Базовый класс для conditioning
│   │   │   ├── canny_conditioning.py    # 🔥 Canny edge detection (РЕАЛЬНЫЙ)
│   │   │   ├── depth_conditioning.py    # 🔥 Depth estimation (РЕАЛЬНЫЙ)
│   │   │   ├── segmentation_conditioning.py # 🔥 Сегментация (РЕАЛЬНЫЙ)
│   │   │   ├── scribble_conditioning.py # 🔥 Scribble generation (РЕАЛЬНЫЙ)
│   │   │   ├── preprocessing.py         # 🔥 Утилиты предобработки
│   │   │   └── evaluation.py            # 🔥 Оценка качества conditioning
│   │   ├── prompt/                       # 🔥 РЕАЛЬНЫЙ Prompt engineering
│   │   │   ├── __init__.py
│   │   │   ├── prompt_builder.py        # 🔥 РЕАЛЬНЫЙ построитель промптов
│   │   │   └── style_definitions.py     # 🔥 РЕАЛЬНЫЕ стилевые определения
│   │   ├── semantic/                     # 🔥 Семантический анализ (заготовка)
│   │   │   ├── __init__.py
│   │   │   ├── character_analyzer.py    # 🔥 Анализ иероглифов
│   │   │   ├── radical_database.py      # 🔥 База радикалов
│   │   │   └── visual_associations.py   # 🔥 Визуальные ассоциации
│   │   ├── pipeline/                     # 🔥 РЕАЛЬНЫЕ AI Pipeline компоненты
│   │   │   ├── __init__.py
│   │   │   ├── pipeline_controlnet_union_sd_xl.py  # 🔥 Union ControlNet Pipeline
│   │   │   └── pipeline_utils.py        # 🔥 Утилиты pipeline
│   │   └── utils/                        # 🔥 AI утилиты
│   │       ├── __init__.py
│   │       ├── image_preprocessing.py   # 🔥 Предобработка для AI
│   │       ├── tensor_utils.py          # 🔥 Работа с тензорами
│   │       └── batch_processor.py       # 🔥 Batch обработка
│   ├── models/                           # 🔥 РЕАЛЬНЫЕ AI модели
│   │   ├── __init__.py
│   │   ├── model_loader.py              # 🔥 РЕАЛЬНАЯ загрузка моделей
│   │   ├── gpu_manager.py               # 🔥 РЕАЛЬНОЕ GPU управление
│   │   ├── model_cache.py               # 🔥 Кэширование моделей
│   │   ├── model_config.py              # 🔥 Конфигурации моделей
│   │   └── controlnet_union.py          # 🔥 Union ControlNet модель
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py
│   │   ├── dependencies.py
│   │   └── exceptions.py
│   └── utils/
│       ├── __init__.py
│       ├── config_holder.py
│       ├── image_utils.py               # 🔥 РЕАЛЬНЫЙ ImageProcessor с AI
│       └── logger.py                    # 🔥 Из common
├── conf/
│   ├── __init__.py
│   └── config/
│       ├── __init__.py
│       ├── default.yaml
│       ├── api.yaml                     # 🔥 РЕАЛЬНЫЕ AI настройки
│       ├── generation.yaml              # 🔥 Базовые настройки генерации
│       ├── ai_generation.yaml           # 🔥 ПОЛНАЯ РЕАЛЬНАЯ AI конфигурация
│       └── logging.yaml
├── requirements_cpu.txt                 # Базовые зависимости
├── requirements_gpu.txt                 # 🔥 РЕАЛЬНЫЕ AI зависимости с GPU
├── environment.yml                      # Базовое окружение  
├── environment_gpu.yml                  # 🔥 РЕАЛЬНОЕ AI окружение с GPU
├── logs/
│   └── writing_service.log
├── temp/
│   ├── generated_images/                # 🔥 РЕАЛЬНЫЕ сгенерированные AI изображения
│   └── model_cache/                     # 🔥 Кэш AI моделей
├── cache/                               # 🔥 РЕАЛЬНЫЕ AI кэши
│   ├── huggingface/                     # HuggingFace модели (Stable Diffusion XL, Union ControlNet)
│   ├── transformers/                    # Transformers кэш
│   ├── torch/                           # PyTorch кэш
│   └── pytorch_kernel_cache/            # Compiled CUDA kernels
└── tests/
    ├── __init__.py
    ├── conftest.py
    ├── test_health.py
    ├── test_writing_images.py
    ├── test_validation_service.py        # 🔥 РЕАЛЬНЫЕ тесты валидации
    ├── test_writing_image_service.py     # 🔥 РЕАЛЬНЫЕ тесты AI генерации
    ├── test_ai/                          # 🔥 РЕАЛЬНЫЕ AI тесты
    │   ├── __init__.py
    │   ├── test_ai_image_generator.py    # 🔥 Тесты AI генератора
    │   ├── test_multi_controlnet.py      # 🔥 Тесты Union ControlNet
    │   ├── test_conditioning/            # 🔥 Тесты conditioning
    │   │   ├── test_canny_conditioning.py
    │   │   ├── test_depth_conditioning.py
    │   │   ├── test_segmentation_conditioning.py
    │   │   └── test_scribble_conditioning.py
    │   ├── test_prompt/                  # 🔥 Тесты prompt engineering
    │   │   ├── test_prompt_builder.py
    │   │   └── test_style_definitions.py
    │   └── test_models/                  # 🔥 Тесты AI моделей
    │       ├── test_model_loader.py
    │       └── test_gpu_manager.py
    ├── integration/                      # 🔥 РЕАЛЬНЫЕ интеграционные AI тесты
    │   ├── __init__.py
    │   ├── test_full_ai_pipeline.py      # 🔥 Полный AI pipeline
    │   └── test_gpu_scenarios.py         # 🔥 GPU сценарии
    ├── fixtures/                         # 🔥 Тестовые данные
    │   ├── __init__.py
    │   ├── sample_characters.py          # 🔥 Тестовые иероглифы
    │   └── mock_models.py                # 🔥 Mock AI модели
    └── benchmarks/                       # 🔥 РЕАЛЬНЫЕ Performance тесты
        ├── __init__.py
        ├── performance_suite.py          # 🔥 AI performance benchmarks
        └── memory_profiling.py           # 🔥 GPU memory профилирование
```

## Фронтенд (Telegram-бот)

```
frontend/
├── app/
│   ├── __init__.py
│   ├── main_frontend.py
│   ├── bot/
│   │   ├── __init__.py
│   │   ├── bot.py
│   │   ├── states/
│   │   │   ├── __init__.py
│   │   │   └── centralized_states.py
│   │   ├── handlers/
│   │   │   ├── __init__.py
│   │   │   ├── admin_handlers.py
│   │   │   ├── common_handlers.py
│   │   │   ├── language_handlers.py
│   │   │   ├── study_handlers.py
│   │   │   ├── user_handlers.py
│   │   │   ├── admin/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── admin_basic_handlers.py
│   │   │   │   ├── admin_language_handlers.py
│   │   │   │   ├── admin_upload_handlers.py
│   │   │   │   ├── admin_word_handlers.py
│   │   │   │   ├── admin_ai_handlers.py  # 🔥 НОВЫЙ: AI администрирование
│   │   │   │   └── file_upload/
│   │   │   │       ├── __init__.py
│   │   │   │       ├── language_router.py
│   │   │   │       ├── file_router.py
│   │   │   │       ├── column_router.py
│   │   │   │       ├── column_type_router.py
│   │   │   │       ├── settings_router.py
│   │   │   │       └── template_router.py
│   │   │   ├── user/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── basic_handlers.py
│   │   │   │   ├── help_handlers.py
│   │   │   │   ├── hint_handlers.py
│   │   │   │   ├── settings_handlers.py
│   │   │   │   ├── stats_handlers.py
│   │   │   │   └── ai_image_handlers.py  # 🔥 НОВЫЙ: AI изображения для пользователей
│   │   │   └── study/
│   │   │       ├── __init__.py
│   │   │       ├── study_commands.py
│   │   │       ├── study_words.py
│   │   │       ├── study_word_actions.py
│   │   │       ├── study_hint_handlers.py
│   │   │       ├── ai_writing_handlers.py  # 🔥 НОВЫЙ: AI генерация в изучении
│   │   │       ├── hint/
│   │   │       │   ├── __init__.py
│   │   │       │   ├── common.py
│   │   │       │   ├── create_handlers.py
│   │   │       │   ├── edit_handlers.py
│   │   │       │   ├── toggle_handlers.py
│   │   │       │   └── unknown.py
│   │   │       └── word_actions/
│   │   │           ├── __init__.py
│   │   │           ├── word_display_actions.py
│   │   │           ├── word_evaluation_actions.py
│   │   │           ├── word_navigation_actions.py
│   │   │           └── word_utility_actions.py
│   │   ├── keyboards/
│   │   │   ├── __init__.py
│   │   │   ├── admin_keyboards.py
│   │   │   ├── user_keyboards.py
│   │   │   ├── inline_keyboards.py
│   │   │   ├── study_keyboards.py
│   │   │   └── ai_keyboards.py          # 🔥 НОВЫЙ: клавиатуры для AI функций
│   │   └── middleware/
│   │       ├── __init__.py
│   │       └── auth_middleware.py
│   ├── api/
│   │   ├── __init__.py
│   │   ├── client.py                     # 🔥 ОБНОВЛЕН: реальная Writing Service интеграция
│   │   └── models/
│   │       ├── __init__.py
│   │       ├── language.py
│   │       ├── user.py
│   │       ├── word.py
│   │       └── ai_models.py             # 🔥 НОВЫЙ: модели для AI запросов
│   └── utils/
│       ├── __init__.py
│       ├── admin_utils.py
│       ├── api_utils.py
│       ├── audio_utils.py
│       ├── callback_constants.py
│       ├── error_utils.py
│       ├── ffmpeg_utils.py
│       ├── file_utils.py
│       ├── formatting_utils.py
│       ├── hint_constants.py
│       ├── hint_settings_utils.py
│       ├── logger.py
│       ├── message_utils.py
│       ├── settings_utils.py
│       ├── state_models.py
│       ├── user_utils.py
│       ├── voice_recognition.py
│       ├── voice_utils.py
│       ├── word_data_utils.py
│       ├── big_word_generator.py         # Генератор крупных изображений слов
│       └── ai_utils.py                   # 🔥 НОВЫЙ: утилиты для AI интеграции
├── conf/
│   ├── __init__.py
│   └── config/
│       ├── __init__.py
│       ├── default.yaml
│       ├── bot.yaml
│       ├── api.yaml                      # 🔥 ОБНОВЛЕН: реальный Writing Service URL
│       ├── logging.yaml
│       ├── learning.yaml
│       └── ai.yaml                       # 🔥 НОВЫЙ: настройки AI интеграции
├── logs/
│   └── app.log
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_main.py
│   ├── test_bot_commands.py
│   ├── bot_test_framework/
│   │   ├── __init__.py
│   │   ├── bot_actions.py
│   │   ├── bot_test_context.py
│   │   ├── command_handler.py
│   │   ├── message_handler.py
│   │   ├── callback_handler.py
│   │   ├── bot_test_scenario.py
│   │   ├── bot_test_framework.py
│   │   └── scenario_executor.py
│   ├── test_scenarios/
│   │   ├── __init__.py
│   │   ├── test_user_scenario.py
│   │   ├── test_ai_generation_scenario.py  # 🔥 НОВЫЙ: AI тесты сценариев
│   │   └── scenarios/
│   │       ├── start_help_settings.yaml
│   │       ├── settings_toggle.yaml
│   │       └── ai_generation_flow.yaml  # 🔥 НОВЫЙ: AI генерация сценарий
│   ├── test_handlers/
│   │   ├── test_user/
│   │   │   ├── test_user_handlers.py
│   │   │   ├── test_basic_handlers.py
│   │   │   ├── test_help_handlers.py
│   │   │   ├── test_settings_handlers.py
│   │   │   ├── test_stats_handlers.py
│   │   │   └── test_ai_image_handlers.py  # 🔥 НОВЫЙ: тесты AI изображений
│   │   ├── test_admin/
│   │   │   ├── test_admin_basic_handlers.py
│   │   │   ├── test_admin_language_handlers.py
│   │   │   ├── test_admin_upload_handlers.py
│   │   │   ├── test_admin_upload_column_handlers.py
│   │   │   ├── test_admin_upload_routers.py
│   │   │   ├── test_admin_word_handlers.py
│   │   │   └── test_admin_ai_handlers.py  # 🔥 НОВЫЙ: тесты AI администрирования
│   │   └── test_study/
│   │       ├── __init__.py
│   │       ├── test_study_commands.py
│   │       ├── test_study_words.py
│   │       ├── test_ai_writing_handlers.py  # 🔥 НОВЫЙ: тесты AI в изучении
│   │       ├── test_word_actions/
│   │       │   ├── test_word_display_actions.py
│   │       │   ├── test_word_evaluation_actions.py
│   │       │   ├── test_word_navigation_actions.py
│   │       │   └── test_word_utility_actions.py
│   │       └── test_hint/
│   │           ├── test_create_handlers.py
│   │           ├── test_edit_handlers.py
│   │           ├── test_toggle_handlers.py
│   │           └── test_common.py
│   ├── test_utils/
│   │   ├── test_admin_utils.py
│   │   ├── test_callback_constants.py
│   │   ├── test_centralized_states.py
│   │   ├── test_voice_utils.py
│   │   ├── test_big_word_generator.py    # Тесты генератора изображений
│   │   ├── test_hint_settings_utils.py
│   │   ├── test_state_models.py
│   │   ├── test_batch_loading.py
│   │   └── test_ai_utils.py              # 🔥 НОВЫЙ: тесты AI утилит
│   └── test_api/
│       ├── __init__.py
│       ├── test_client.py               # 🔥 ОБНОВЛЕН: реальные Writing Service тесты
│       ├── test_ai_integration.py       # 🔥 НОВЫЙ: интеграционные AI тесты
│       └── test_models.py
└── watch_and_reload.py
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

## Служебные скрипты

```
scripts/
├── __init__.py
├── init_db.py
├── seed_data.py
├── run_tests.py
├── migrate_data.py
├── admin_manager.py
├── create_user_language_settings_collection.py
├── ai_model_downloader.py               # 🔥 НОВЫЙ: загрузка AI моделей
├── gpu_benchmark.py                     # 🔥 НОВЫЙ: бенчмарк GPU
├── ai_warmup.py                         # 🔥 НОВЫЙ: прогрев AI моделей
├── ai_model_optimizer.py               # 🔥 НОВЫЙ: оптимизация AI моделей
└── ai_cache_cleaner.py                  # 🔥 НОВЫЙ: очистка AI кэшей
```
