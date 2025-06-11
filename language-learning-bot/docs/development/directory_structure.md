# Структура каталогов и файлов проекта

## Корневой каталог

```
language-learning-bot/
├── README.md
├── .gitignore
├── requirements.txt
├── requirements_cpu.txt                  # Базовые зависимости  
├── requirements_gpu.txt                  # 🆕 AI зависимости для GPU
├── environment.yml                       # Базовое окружение
├── environment_gpu.yml                   # 🆕 AI окружение с GPU поддержкой
├── docker-compose.yml
├── .env.example
├── .env
├── pyproject.toml
├── setup.py
├── start_1_db.sh
├── start_2_backend.sh
├── start_3_frontend.sh
├── start_4_writing_service.sh            # 🆕 Запуск AI сервиса
├── start_3_frontend_auto_reload.sh
├── setup_watchdog.sh
├── run_export_env.sh
├── run_tests.sh
├── .backend.pid
├── .frontend.pid
├── .writing_service.pid                  # 🆕 PID файл AI сервиса
├── docs/
├── frontend/
├── backend/
├── writing_service/                      # 🆕 AI микросервис
├── common/
└── scripts/
```

## Каталог документации

```
docs/
├── README.md
├── summary.md
├── architecture.md                       # ОБНОВЛЕН: AI архитектура
├── project_description.md                # ОБНОВЛЕН: AI возможности  
├── backlog.md
│
├── user/
│   ├── quick_start.md
│   ├── commands.md
│   └── learning_guide.md
│
├── installation/
│   ├── installation_guide.md             # ОБНОВЛЕН: AI зависимости
│   ├── environment_setup.md              # ОБНОВЛЕН: GPU настройки
│   └── mongodb_setup.md
│
├── running/
│   ├── running_guide.md                  # ОБНОВЛЕН: Writing Service
│   ├── scripts_reference.md
│   ├── auto_reload.md
│   ├── deployment_guide.md
│   ├── gpu_requirements.md               # 🆕 GPU требования
│   ├── performance_tuning.md             # 🆕 AI оптимизация
│   └── monitoring_ai.md                  # 🆕 AI мониторинг
│
├── api/
│   ├── api_reference.md
│   ├── backend_api.md
│   ├── writing_service_api.md             # ОБНОВЛЕН: реальные AI API
│   └── ai_generation_api.md              # 🆕 AI компоненты API
│
├── development/
│   ├── testing_guide.md
│   ├── bot_test_framework.md
│   ├── configuration.md
│   ├── directory_structure.md            # ОБНОВЛЕН: AI структура
│   ├── router_organization.md
│   ├── show_big.md
│   ├── meta_states_guide.md
│   ├── ai_configuration.md               # 🆕 AI настройки
│   ├── gpu_optimization.md               # 🆕 GPU оптимизация
│   ├── troubleshooting_ai.md             # 🆕 AI troubleshooting
│   ├── ai_testing_guide.md               # 🆕 AI тестирование
│   └── model_management.md               # 🆕 Управление моделями
│
└── functionality/
    ├── bot_commands.md
    ├── admin_tools.md
    ├── learning_system.md                # ОБНОВЛЕН: AI интеграция
    └── ai_image_generation.md            # 🆕 AI генерация изображений
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
│   │   │   │   └── stats_handlers.py
│   │   │   └── study/
│   │   │       ├── __init__.py
│   │   │       ├── study_commands.py
│   │   │       ├── study_words.py
│   │   │       ├── study_word_actions.py
│   │   │       ├── study_hint_handlers.py
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
│   │   │   └── study_keyboards.py
│   │   └── middleware/
│   │       ├── __init__.py
│   │       └── auth_middleware.py
│   ├── api/
│   │   ├── __init__.py
│   │   ├── client.py                     # ОБНОВЛЕН: Writing Service интеграция
│   │   └── models/
│   │       ├── __init__.py
│   │       ├── language.py
│   │       ├── user.py
│   │       └── word.py
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
│       └── big_word_generator.py         # Генератор крупных изображений слов
├── conf/
│   ├── __init__.py
│   └── config/
│       ├── __init__.py
│       ├── default.yaml
│       ├── bot.yaml
│       ├── api.yaml                      # ОБНОВЛЕН: Writing Service URL
│       ├── logging.yaml
│       └── learning.yaml
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
│   │   └── scenarios/
│   │       ├── start_help_settings.yaml
│   │       └── settings_toggle.yaml
│   ├── test_handlers/
│   │   ├── test_user/
│   │   │   ├── test_user_handlers.py
│   │   │   ├── test_basic_handlers.py
│   │   │   ├── test_help_handlers.py
│   │   │   ├── test_settings_handlers.py
│   │   │   └── test_stats_handlers.py
│   │   ├── test_admin/
│   │   │   ├── test_admin_basic_handlers.py
│   │   │   ├── test_admin_language_handlers.py
│   │   │   ├── test_admin_upload_handlers.py
│   │   │   ├── test_admin_upload_column_handlers.py
│   │   │   ├── test_admin_upload_routers.py
│   │   │   └── test_admin_word_handlers.py
│   │   └── test_study/
│   │       ├── __init__.py
│   │       ├── test_study_commands.py
│   │       ├── test_study_words.py
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
│   │   └── test_batch_loading.py
│   └── test_api/
│       ├── __init__.py
│       ├── test_client.py               # ОБНОВЛЕН: Writing Service тесты
│       └── test_models.py
└── watch_and_reload.py
```

## Бэкенд (REST API)

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── api/
│   │   ├── __init__.py
│   │   ├── routes/
│   │   │   ├── __init__.py
│   │   │   ├── languages.py
│   │   │   ├── users.py
│   │   │   ├── words.py
│   │   │   └── statistics.py
│   │   ├── schemas/
│   │   │   ├── __init__.py
│   │   │   ├── language.py
│   │   │   ├── user.py
│   │   │   ├── word.py
│   │   │   └── statistics.py
│   ├── db/
│   │   ├── __init__.py
│   │   ├── database.py
│   │   ├── repositories/
│   │   │   ├── __init__.py
│   │   │   ├── base_repository.py
│   │   │   ├── language_repository.py
│   │   │   ├── user_repository.py
│   │   │   ├── word_repository.py
│   │   │   └── statistics_repository.py
│   ├── services/
│   │   ├── __init__.py
│   │   ├── language_service.py
│   │   ├── user_service.py
│   │   ├── word_service.py
│   │   ├── statistics_service.py
│   │   └── excel_service.py
│   ├── core/
│   │   ├── __init__.py
│   │   ├── dependencies.py
│   │   └── exceptions.py
│   └── utils/
│       ├── __init__.py
│       └── logger.py
├── conf/
│   ├── __init__.py
│   └── config/
│       ├── __init__.py
│       ├── default.yaml
│       ├── api.yaml
│       ├── database.yaml
│       └── logging.yaml
├── logs/
│   └── backend.log
└── tests/
    ├── __init__.py
    ├── conftest.py
    ├── test_api/
    ├── test_services/
    └── test_repositories/
```

## 🆕 Writing Service (AI микросервис генерации картинок)

```
writing_service/
├── app/
│   ├── __init__.py
│   ├── main_writing_service.py           # ОБНОВЛЕН: реальная AI инициализация
│   ├── api/
│   │   ├── __init__.py
│   │   └── routes/
│   │       ├── __init__.py
│   │       ├── models/
│   │       │   ├── __init__.py
│   │       │   ├── requests.py           # AI запросы
│   │       │   └── responses.py          # AI ответы
│   │       ├── writing_images.py         # ОБНОВЛЕН: реальная AI генерация
│   │       └── health.py                 # ОБНОВЛЕН: AI health checks
│   ├── ai/                               # 🆕 AI компоненты
│   │   ├── __init__.py
│   │   ├── ai_image_generator.py         # 🆕 Основной AI генератор
│   │   ├── multi_controlnet_pipeline.py  # 🆕 Multi-ControlNet pipeline
│   │   ├── conditioning/                 # 🆕 Conditioning генераторы
│   │   │   ├── __init__.py
│   │   │   ├── base_conditioning.py     # 🆕 Базовый класс
│   │   │   ├── canny_conditioning.py    # 🆕 Canny edge detection
│   │   │   ├── depth_conditioning.py    # 🆕 Depth estimation
│   │   │   ├── segmentation_conditioning.py # 🆕 Сегментация
│   │   │   ├── scribble_conditioning.py # 🆕 Scribble generation
│   │   │   ├── preprocessing.py         # 🆕 Общие утилиты
│   │   │   └── evaluation.py            # 🆕 Качество conditioning
│   │   ├── prompt/                       # 🆕 Prompt engineering
│   │   │   ├── __init__.py
│   │   │   ├── prompt_builder.py        # 🆕 Построение промптов
│   │   │   └── style_definitions.py     # 🆕 Стилевые определения
│   │   ├── semantic/                     # 🆕 Семантический анализ
│   │   │   ├── __init__.py
│   │   │   ├── character_analyzer.py    # 🆕 Анализ иероглифов
│   │   │   ├── radical_database.py      # 🆕 База радикалов
│   │   │   └── visual_associations.py   # 🆕 Визуальные ассоциации
│   │   └── utils/                        # 🆕 AI утилиты
│   │       ├── __init__.py
│   │       ├── image_preprocessing.py   # 🆕 Предобработка изображений
│   │       ├── tensor_utils.py          # 🆕 Работа с тензорами
│   │       └── batch_processor.py       # 🆕 Batch обработка
│   ├── models/                           # 🆕 AI модели
│   │   ├── __init__.py
│   │   ├── model_loader.py              # 🆕 ОБНОВЛЕН: реальная загрузка моделей
│   │   ├── gpu_manager.py               # 🆕 ОБНОВЛЕН: реальное GPU управление
│   │   ├── model_cache.py               # 🆕 Кэширование моделей
│   │   └── model_config.py              # 🆕 Конфигурации моделей
│   ├── services/
│   │   ├── __init__.py
│   │   ├── writing_image_service.py     # ОБНОВЛЕН: реальная AI интеграция
│   │   └── validation_service.py        # ОБНОВЛЕН: универсальная поддержка языков
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py
│   │   ├── dependencies.py
│   │   └── exceptions.py
│   └── utils/
│       ├── __init__.py
│       ├── config_holder.py
│       ├── image_utils.py               # ОБНОВЛЕН: ImageProcessor с AI
│       └── logger.py                    # ОБНОВЛЕН: из common
├── conf/
│   ├── __init__.py
│   └── config/
│       ├── __init__.py
│       ├── default.yaml
│       ├── api.yaml                     # ОБНОВЛЕН: AI настройки
│       ├── generation.yaml              # ОБНОВЛЕН: убраны ограничения языков
│       ├── ai_generation.yaml           # 🆕 Полная AI конфигурация
│       └── logging.yaml
├── requirements_cpu.txt                 # Базовые зависимости
├── requirements_gpu.txt                 # 🆕 AI зависимости с GPU
├── environment.yml                      # Базовое окружение  
├── environment_gpu.yml                  # 🆕 AI окружение с GPU
├── logs/
│   └── writing_service.log
├── temp/
│   ├── generated_images/                # Временные AI изображения
│   └── model_cache/                     # 🆕 Кэш AI моделей
├── cache/                               # 🆕 AI кэши
│   ├── huggingface/                     # HuggingFace модели
│   ├── transformers/                    # Transformers кэш
│   ├── torch/                           # PyTorch кэш
│   └── pytorch_kernel_cache/            # Compiled kernels
└── tests/
    ├── __init__.py
    ├── conftest.py
    ├── test_health.py
    ├── test_writing_images.py
    ├── test_validation_service.py        # ОБНОВЛЕН: тесты универсальной поддержки
    ├── test_writing_image_service.py     # ОБНОВЛЕН: тесты реальной AI генерации
    ├── test_ai/                          # 🆕 AI тесты
    │   ├── __init__.py
    │   ├── test_ai_image_generator.py    # 🆕 Тесты AI генератора
    │   ├── test_multi_controlnet.py      # 🆕 Тесты Multi-ControlNet
    │   ├── test_conditioning/            # 🆕 Тесты conditioning
    │   │   ├── test_canny_conditioning.py
    │   │   ├── test_depth_conditioning.py
    │   │   ├── test_segmentation_conditioning.py
    │   │   └── test_scribble_conditioning.py
    │   ├── test_prompt/                  # 🆕 Тесты prompt engineering
    │   │   ├── test_prompt_builder.py
    │   │   └── test_style_definitions.py
    │   └── test_models/                  # 🆕 Тесты AI моделей
    │       ├── test_model_loader.py
    │       └── test_gpu_manager.py
    ├── integration/                      # 🆕 Интеграционные AI тесты
    │   ├── __init__.py
    │   ├── test_full_ai_pipeline.py      # 🆕 Полный AI pipeline
    │   └── test_gpu_scenarios.py         # 🆕 GPU сценарии
    ├── fixtures/                         # 🆕 Тестовые данные
    │   ├── __init__.py
    │   ├── sample_characters.py          # 🆕 Тестовые иероглифы
    │   └── mock_models.py                # 🆕 Mock AI модели
    └── benchmarks/                       # 🆕 Performance тесты
        ├── __init__.py
        ├── performance_suite.py          # 🆕 AI performance
        └── memory_profiling.py           # 🆕 GPU memory профилирование
```

## Общие модули (Common)

```
common/
├── __init__.py
├── utils/
│   ├── __init__.py
│   ├── font_utils.py                    # 🆕 НОВЫЙ: Общий FontManager для всех сервисов
│   └── logger.py                        # ОБНОВЛЕН: поддержка AI логирования
└── tests/
    ├── __init__.py
    ├── conftest.py
    ├── test_utils_logger.py
    └── test_font_utils.py               # 🆕 НОВЫЙ: Тесты FontManager
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
├── ai_model_downloader.py               # 🆕 Загрузка AI моделей
├── gpu_benchmark.py                     # 🆕 Бенчмарк GPU
└── ai_warmup.py                         # 🆕 Прогрев AI моделей
```

## 🆕 Конфигурационные файлы для AI

### Writing Service AI конфигурация:
```
writing_service/conf/config/
├── ai_generation.yaml                   # 🆕 Полная AI конфигурация
│   ├── models:                          # AI модели
│   │   ├── base_model                   # Stable Diffusion XL
│   │   ├── controlnet_models            # ControlNet модели
│   │   └── auxiliary_models             # Вспомогательные модели
│   ├── generation:                      # Параметры генерации
│   │   ├── num_inference_steps
│   │   ├── guidance_scale
│   │   └── conditioning_weights
│   ├── conditioning:                    # Настройки conditioning
│   │   ├── canny                        # Edge detection
│   │   ├── depth                        # Depth estimation  
│   │   ├── segmentation                 # Сегментация
│   │   └── scribble                     # Scribble generation
│   ├── semantic_analysis:               # Семантический анализ
│   │   ├── unihan                       # Unicode база
│   │   ├── radical_kangxi               # Радикалы
│   │   └── visual_associations          # Визуальные ассоциации
│   ├── gpu:                             # GPU настройки
│   │   ├── device
│   │   ├── memory_efficient
│   │   ├── batch_size
│   │   └── optimizations
│   ├── prompt_engineering:              # Prompt engineering
│   │   ├── base_templates
│   │   ├── style_modifiers
│   │   └── semantic_mappings
│   └── monitoring:                      # Мониторинг AI
│       ├── performance_tracking
│       └── export_results
```
