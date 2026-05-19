# Структура каталогов и файлов проекта

## Корневой каталог

```
language-learning-bot/
├── README.md
├── docker-compose.yml
├── environment.yml
├── pyproject.toml
├── requirements.txt
├── setup.py
├── run_export_env.sh
├── run_tests.sh
├── start_1_db.sh
├── start_2_backend.sh
├── start_3_frontend.sh
├── start_3_frontend_auto_reload.sh
├── start_4_writing_images_service.sh
├── create_project_structure.py
├── docs/
├── frontend/
├── backend/
├── writing_images_service/
├── common/
└── scripts/
```

## Каталог документации

```
docs/
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
│   ├── mongodb_setup.md
│   └── gpu_requirements.md
│
├── running/
│   ├── running_guide.md
│   ├── scripts_reference.md
│   ├── auto_reload.md
│   └── deployment_guide.md
│
├── api/
│   ├── api_reference.md
│   ├── backend_api.md
│   └── api_writing_image_service.md
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
    ├── learning_system.md
    └── ai_image_generation.md
```

## Backend (REST API)

```
backend/
├── app/
│   ├── __init__.py
│   ├── main_backend.py
│   ├── api/
│   │   ├── __init__.py
│   │   ├── routes/
│   │   │   ├── __init__.py
│   │   │   ├── languages.py
│   │   │   ├── words.py
│   │   │   ├── users.py
│   │   │   ├── statistics.py
│   │   │   ├── sounds.py
│   │   │   └── user_language_settings.py
│   │   ├── schemas/
│   │   │   ├── __init__.py
│   │   │   ├── language.py
│   │   │   ├── word.py
│   │   │   ├── user.py
│   │   │   ├── statistics.py
│   │   │   └── user_language_settings.py
│   │   └── models/
│   │       ├── __init__.py
│   │       ├── language.py
│   │       ├── word.py
│   │       ├── user.py
│   │       ├── statistics.py
│   │       └── user_language_settings.py (в db/models/)
│   ├── services/
│   │   ├── __init__.py
│   │   ├── language_service.py
│   │   ├── word_service.py
│   │   ├── user_service.py
│   │   ├── statistics_service.py
│   │   ├── user_language_settings_service.py
│   │   ├── sound_service.py
│   │   └── excel_service.py
│   ├── db/
│   │   ├── __init__.py
│   │   ├── database.py
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── language.py
│   │   │   ├── word.py
│   │   │   ├── user.py
│   │   │   └── statistics.py
│   │   └── repositories/
│   │       ├── __init__.py
│   │       ├── base.py
│   │       ├── language_repository.py
│   │       ├── word_repository.py
│   │       ├── user_repository.py
│   │       ├── statistics_repository.py
│   │       └── user_language_settings_repository.py
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py
│   │   ├── dependencies.py
│   │   ├── exceptions.py
│   │   └── security.py
│   └── utils/
│       ├── __init__.py
│       ├── excel_parser.py
│       └── logger.py
├── conf/
│   ├── __init__.py
│   ├── config.py
│   └── config/
│       └── __init__.py
├── alembic/
│   └── env.py
├── requirements.txt
├── environment.yml
└── tests/
    ├── __init__.py
    ├── conftest.py
    ├── test_api/
    │   ├── __init__.py
    │   ├── test_languages.py
    │   ├── test_words.py
    │   ├── test_users.py
    │   └── test_statistics.py
    ├── test_services/
    │   ├── __init__.py
    │   ├── test_language_service.py
    │   ├── test_word_service.py
    │   ├── test_user_service.py
    │   └── test_statistics_service.py
    └── test_repositories/
        ├── __init__.py
        ├── test_language_repository.py
        ├── test_word_repository.py
        ├── test_user_repository.py
        └── test_statistics_repository.py
```

## Фронтенд (Telegram-бот)

```
frontend/
├── app/
│   ├── __init__.py
│   ├── main_frontend.py
│   ├── watch_and_reload.py
│   ├── api/
│   │   ├── __init__.py
│   │   ├── client.py
│   │   ├── writing_image_client.py
│   │   └── models/
│   │       ├── __init__.py
│   │       ├── language.py
│   │       ├── user.py
│   │       ├── word.py
│   │       └── writing_image.py
│   ├── bot/
│   │   ├── __init__.py
│   │   ├── bot.py
│   │   ├── handlers/
│   │   │   ├── __init__.py
│   │   │   ├── admin_handlers.py
│   │   │   ├── common_handlers.py
│   │   │   ├── language_handlers.py
│   │   │   ├── study_handlers.py
│   │   │   ├── unknown_handlers.py
│   │   │   ├── user_handlers.py
│   │   │   ├── admin/
│   │   │   │   ├── admin_basic_handlers.py
│   │   │   │   ├── admin_export_handlers.py
│   │   │   │   ├── admin_language_handlers.py
│   │   │   │   ├── admin_messaging_handlers.py
│   │   │   │   ├── admin_upload_handlers.py
│   │   │   │   ├── admin_word_handlers.py
│   │   │   │   └── file_upload/
│   │   │   │       ├── __init__.py
│   │   │   │       ├── column_configuration.py
│   │   │   │       ├── column_type_processing.py
│   │   │   │       ├── file_processing.py
│   │   │   │       ├── language_selection.py
│   │   │   │       ├── settings_management.py
│   │   │   │       └── template_processing.py
│   │   │   ├── study/
│   │   │   │   ├── study_commands.py
│   │   │   │   ├── study_hint_handlers.py
│   │   │   │   ├── study_word_actions.py
│   │   │   │   ├── study_words.py
│   │   │   │   ├── hint/
│   │   │   │   │   ├── __init__.py
│   │   │   │   │   ├── common.py
│   │   │   │   │   ├── create_handlers.py
│   │   │   │   │   ├── edit_handlers.py
│   │   │   │   │   ├── toggle_handlers.py
│   │   │   │   │   └── unknown.py
│   │   │   │   └── word_actions/
│   │   │   │       ├── word_display_actions.py
│   │   │   │       ├── word_evaluation_actions.py
│   │   │   │       ├── word_navigation_actions.py
│   │   │   │       └── word_utility_actions.py
│   │   │   └── user/
│   │   │       ├── __init__.py
│   │   │       ├── basic_handlers.py
│   │   │       ├── help_handlers.py
│   │   │       ├── hint_handlers.py
│   │   │       ├── settings_handlers.py
│   │   │       └── stats_handlers.py
│   │   ├── keyboards/
│   │   │   ├── __init__.py
│   │   │   ├── admin_keyboards.py
│   │   │   ├── study_keyboards.py
│   │   │   └── user_keyboards.py
│   │   ├── middleware/
│   │   │   ├── __init__.py
│   │   │   └── auth_middleware.py
│   │   └── states/
│   │       ├── __init__.py
│   │       └── centralized_states.py
│   └── utils/
│       ├── __init__.py
│       ├── admin_utils.py
│       ├── api_utils.py
│       ├── audio_utils.py
│       ├── big_word_generator.py
│       ├── callback_constants.py
│       ├── chart_generator.py
│       ├── config_holder.py
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
│       ├── statistics_utils.py
│       ├── user_utils.py
│       ├── voice_recognition.py
│       ├── voice_utils.py
│       ├── word_data_utils.py
│       └── writing_image_utils.py
├── conf/
│   ├── __init__.py
│   └── config/
│       ├── __init__.py
│       ├── default.yaml
│       ├── bot.yaml
│       ├── api.yaml
│       ├── logging.yaml
│       └── learning.yaml
├── requirements.txt
├── environment.yml
└── tests/
    ├── __init__.py
    ├── conftest.py
    ├── bot_test_framework/
    │   ├── __init__.py
    │   ├── api_mock_setup.py
    │   ├── bot_actions.py
    │   ├── bot_actions_keyboard.py
    │   ├── bot_test_context.py
    │   ├── bot_test_framework.py
    │   ├── bot_test_scenario.py
    │   ├── callback_handler.py
    │   ├── command_handler.py
    │   ├── handlers_router.py
    │   ├── handlers_setup.py
    │   ├── handlers_utils.py
    │   ├── message_handler.py
    │   └── scenario_executor.py
    ├── test_api/
    │   ├── __init__.py
    │   ├── test_client_private.py
    │   ├── test_language_client.py
    │   ├── test_progress_client.py
    │   ├── test_statistics_client.py
    │   ├── test_upload_file_client.py
    │   ├── test_user_client.py
    │   └── test_word_client.py
    ├── test_handlers/
    │   ├── __init__.py
    │   ├── test_language_handlers.py
    │   ├── test_admin/
    │   │   ├── test_admin_basic_handlers.py
    │   │   ├── test_admin_handlers.py
    │   │   ├── test_admin_language_handlers.py
    │   │   ├── test_admin_upload_column_handlers.py
    │   │   ├── test_admin_upload_handlers.py
    │   │   ├── test_admin_upload_language_handlers.py
    │   │   ├── test_admin_upload_routers.py
    │   │   ├── test_admin_upload_setting_handlers.py
    │   │   └── test_admin_word_handlers.py
    │   ├── test_study/
    │   │   ├── test_study_handlers.py
    │   │   ├── test_study_hint_edit_handlers.py
    │   │   ├── test_study_hint_handlers.py
    │   │   ├── test_study_hint_toggle_handlers.py
    │   │   └── test_study_word_actions.py
    │   └── test_user/
    │       ├── test_hint_handlers.py
    │       ├── test_stats_handlers.py
    │       ├── test_user_basic_handlers.py
    │       ├── test_user_handlers.py
    │       └── test_user_settings_handlers.py
    ├── test_keyboard/
    │   ├── test_admin_keyboards.py
    │   ├── test_study_keyboards.py
    │   └── test_user_keyboards.py
    ├── test_utils/
    │   ├── test_admin_utils.py
    │   ├── test_api_utils.py
    │   ├── test_audio_utils.py
    │   ├── test_error_utils.py
    │   ├── test_ffmpeg_utils.py
    │   ├── test_formatting_utils.py
    │   ├── test_hint_constants.py
    │   ├── test_logger.py
    │   ├── test_settings_utils.py
    │   ├── test_state_models.py
    │   ├── test_voice_recognition.py
    │   └── test_word_data_utils.py
    ├── test_scenarios/
    │   ├── __init__.py
    │   └── test_user_scenario.py
    ├── test_bot.py
    ├── test_bot_commands.py
    └── test_main.py
```

## Writing Images Service (AI микросервис генерации изображений)

```
writing_images_service/
├── app/
│   ├── main_writing_service.py
│   ├── api/
│   │   ├── dependencies.py
│   │   └── routes/
│   │       ├── health.py
│   │       ├── writing_images.py
│   │       ├── models/
│   │       │   ├── requests.py
│   │       │   └── responses.py
│   │       └── services/
│   │           ├── validation_service.py
│   │           └── writing_image_service.py
│   ├── ai/
│   │   ├── __init__.py
│   │   ├── ai_image_generator.py
│   │   ├── multi_controlnet_pipeline.py
│   │   ├── controlnet_union_test_multi_control.py
│   │   ├── core/
│   │   │   ├── __init__.py
│   │   │   ├── conditioning_manager.py
│   │   │   ├── generation_config.py
│   │   │   ├── generation_result.py
│   │   │   ├── image_processor.py
│   │   │   ├── model_manager.py
│   │   │   ├── prompt_manager.py
│   │   │   └── translation_manager.py
│   │   ├── services/
│   │   │   └── translation_service.py
│   │   ├── conditioning/
│   │   │   ├── __init__.py
│   │   │   ├── base_conditioning.py
│   │   │   ├── canny_conditioning.py
│   │   │   ├── depth_conditioning.py
│   │   │   ├── scribble_conditioning.py
│   │   │   └── segmentation_conditioning.py
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── controlnet_union.py
│   │   │   ├── gpu_manager.py
│   │   │   ├── model_loader.py
│   │   │   └── translation_model.py
│   │   ├── pipeline/
│   │   │   └── pipeline_controlnet_union_sd_xl.py
│   │   └── prompt/
│   │       ├── __init__.py
│   │       ├── prompt_builder.py
│   │       └── style_definitions.py
│   ├── core/
│   │   └── exceptions.py
│   └── utils/
│       ├── config_holder.py
│       ├── image_utils.py
│       └── logger.py
├── conf/
│   └── config/
│       ├── ai_generation.yaml
│       ├── api.yaml
│       ├── default.yaml
│       ├── generation.yaml
│       ├── logging.yaml
│       └── translation.yaml
├── fonts/
│   └── NotoSansSC-Regular/
│       └── NotoSansSC-Regular.otf
├── requirements_cpu.txt
├── requirements_gpu.txt
├── environment_cpu.yml
├── environment_gpu.yml
└── tests/
    ├── __init__.py
    ├── conftest.py
    ├── test_api/
    │   ├── __init__.py
    │   ├── test_health.py
    │   └── test_writing_images.py
    └── test_services/
        ├── __init__.py
        ├── test_validation_service.py
        └── test_writing_image_service.py
```

## Общие модули (Common)

```
common/
├── __init__.py
├── utils/
│   ├── __init__.py
│   ├── check_imports.py
│   ├── font_utils.py
│   └── logger.py
└── tests/
    ├── conftest.py
    └── test_logger.py
```

## Служебные скрипты

```
scripts/
├── admin_manager.py
├── create_user_language_settings_collection.py
├── db_indexes.py
├── db_show.py
├── init_db.py
├── run_tests.py
├── seed_data.py
├── test_opus_support.py
├── test_voice_recognition.py
└── update_statistics_index.py
```
