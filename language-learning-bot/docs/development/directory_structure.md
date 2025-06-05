# Структура каталогов и файлов проекта

## Корневой каталог

```
language-learning-bot/
├── README.md
├── .gitignore
├── requirements.txt
├── environment.yml
├── docker-compose.yml
├── .env.example
├── .env
├── pyproject.toml
├── setup.py
├── start_1_db.sh
├── start_2_backend.sh
├── start_3_frontend.sh
├── start_3_frontend_auto_reload.sh
├── setup_watchdog.sh
├── run_export_env.sh
├── run_tests.sh
├── .backend.pid
├── .frontend.pid
├── docs/
├── frontend/
├── backend/
├── common/
└── scripts/
```

## Каталог документации

```
docs/
├── README.md
├── summary.md
├── architecture.md
├── project_description.md
├── backlog.md
│
├── user/
│   ├── quick_start.md
│   ├── commands.md
│   └── learning_guide.md
│
├── installation/
│   ├── installation_guide.md
│   ├── environment_setup.md
│   └── mongodb_setup.md
│
├── running/
│   ├── running_guide.md
│   ├── scripts_reference.md
│   ├── auto_reload.md
│   └── deployment_guide.md
│
├── api/
│   ├── api_reference.md
│   └── backend_api.md
│
├── development/
│   ├── testing_guide.md
│   ├── bot_test_framework.md
│   ├── configuration.md
│   ├── directory_structure.md
│   ├── router_organization.md
│   ├── show_big.md
│   └── meta_states_guide.md
│
└── functionality/
    ├── bot_commands.md
    ├── admin_tools.md
    └── learning_system.md
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
│   │   ├── client.py
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
│       └── word_image_generator.py
├── conf/
│   ├── __init__.py
│   └── config/
│       ├── __init__.py
│       ├── default.yaml
│       ├── bot.yaml
│       ├── api.yaml
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
│   │   ├── test_word_image_generator.py
│   │   ├── test_hint_settings_utils.py
│   │   ├── test_state_models.py
│   │   └── test_batch_loading.py
│   └── test_api/
│       ├── __init__.py
│       ├── test_client.py
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

## Общие модули (Common)

```
common/
├── __init__.py
├── utils/
│   ├── __init__.py
│   ├── logger.py
│   └── [другие утилиты]
└── tests/
    ├── __init__.py
    ├── conftest.py
    └── test_utils_logger.py
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
└── create_user_language_settings_collection.py
```
