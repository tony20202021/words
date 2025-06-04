# Структура каталогов и файлов проекта (ОБНОВЛЕНО v1.4.1)

## Содержание

1. [Корневой каталог](#корневой-каталог)
2. [Каталог документации](#каталог-документации)
3. [Фронтенд (Telegram-бот)](#фронтенд-telegram-бот)
4. [Бэкенд (REST API)](#бэкенд-rest-api)
5. [Общие модули (Common)](#общие-модули-common)
6. [Служебные скрипты](#служебные-скрипты)

## Корневой каталог

```
language-learning-bot/
├── README.md                 # Описание проекта, инструкции по установке и запуску
├── .gitignore                # Список игнорируемых файлов и каталогов
├── requirements.txt          # Зависимости проекта
├── environment.yml           # Конфигурация conda-окружения
├── docker-compose.yml        # Настройки для запуска в Docker (опционально)
├── .env.example              # Пример конфигурации переменных окружения
├── .env                      # Файл с конфигурацией переменных окружения
├── pyproject.toml            # Конфигурация инструментов Python
├── setup.py                  # Скрипт установки проекта
├── start_1_db.sh             # Скрипт для запуска MongoDB
├── start_2_backend.sh        # Скрипт для запуска бэкенда
├── start_3_frontend.sh       # Скрипт для запуска фронтенда
├── start_3_frontend_auto_reload.sh # Скрипт для запуска с автоперезапуском
├── setup_watchdog.sh         # Скрипт для установки зависимостей автоперезапуска
├── run_export_env.sh         # Скрипт для экспорта переменных из .env
├── run_tests.sh              # Скрипт для запуска тестов
├── .backend.pid              # Файл с PID бэкенд-процесса (автоматически)
├── .frontend.pid             # Файл с PID фронтенд-процесса (автоматически)
├── docs/                     # Каталог с документацией
├── frontend/                 # Каталог фронтенда (Telegram-бота)
├── backend/                  # Каталог бэкенда (REST API)
├── common/                   # Каталог общих модулей
└── scripts/                  # Каталог со служебными скриптами
```

## Каталог документации

```
docs/
├── README.md                    # Обзор документации
├── summary.md                   # Структура документации
├── architecture.md              # 🆕 ОБНОВЛЕНО: Архитектура с новыми компонентами
├── project_description.md       # Техническое задание
│
├── installation/                # Установка и настройка
│   ├── installation_guide.md    # Руководство по установке
│   ├── environment_setup.md     # Настройка окружения
│   └── mongodb_setup.md         # Установка и настройка MongoDB
│
├── running/                     # Запуск и управление
│   ├── running_guide.md         # Руководство по запуску
│   ├── scripts_reference.md     # Справочник по скриптам
│   └── auto_reload.md           # Автоматический перезапуск
│
├── api/                         # API и интеграция
│   ├── api_reference.md         # Справочник по API клиенту
│   └── backend_api.md           # Документация по API бэкенда
│
├── development/                 # Разработка и тестирование
│   ├── testing_guide.md         # Руководство по тестированию
│   ├── bot_test_framework.md    # Фреймворк для тестирования бота
│   ├── configuration.md         # Конфигурация с Hydra
│   ├── directory_structure.md   # 🆕 ОБНОВЛЕНО: Структура каталогов (этот файл)
│   ├── migration_guide.md       # Гид по миграции к улучшенной архитектуре
│   └── router_organization.md   # Организация роутеров и обработчиков
│
└── functionality/               # Функциональность бота
    ├── bot_commands.md          # 🆕 ОБНОВЛЕНО: Команды и действия бота
    ├── admin_tools.md           # Инструменты администрирования
    └── learning_system.md       # 🆕 ОБНОВЛЕНО: Система изучения слов
```

## Фронтенд (Telegram-бот)

```
frontend/
├── app/
│   ├── __init__.py
│   ├── main_frontend.py      # Точка входа фронтенда
│   ├── bot/
│   │   ├── __init__.py
│   │   ├── bot.py            # Основной класс бота
│   │   ├── states/           # 🆕 ОБНОВЛЕНО: Централизованные состояния FSM
│   │   │   ├── __init__.py
│   │   │   └── centralized_states.py    # Все состояния FSM + meta-состояния
│   │   ├── handlers/         # 🆕 ПОЛНОСТЬЮ ПЕРЕРАБОТАНО: Модульная система обработчиков
│   │   │   ├── __init__.py
│   │   │   ├── admin_handlers.py        # Объединяет все админ-роутеры
│   │   │   ├── common_handlers.py       # 🆕 Meta-состояния и системные ошибки
│   │   │   ├── language_handlers.py     # Обработчики выбора языка
│   │   │   ├── study_handlers.py        # Объединяет все роутеры изучения
│   │   │   ├── user_handlers.py         # Объединяет пользовательские роутеры
│   │   │   ├── admin/                   # 🆕 Админ-обработчики
│   │   │   │   ├── __init__.py
│   │   │   │   ├── admin_basic_handlers.py      # Базовые команды, статистика, пользователи
│   │   │   │   ├── admin_language_handlers.py   # Управление языками
│   │   │   │   ├── admin_upload_handlers.py     # Загрузка файлов (роутер)
│   │   │   │   ├── admin_word_handlers.py       # 🆕 Управление словами + редактирование из изучения
│   │   │   │   └── file_upload/                 # 🆕 Подмодуль загрузки файлов
│   │   │   │       ├── __init__.py
│   │   │   │       ├── language_router.py       # Выбор языка для загрузки
│   │   │   │       ├── file_router.py           # Обработка файлов
│   │   │   │       ├── column_router.py         # Конфигурация колонок
│   │   │   │       ├── column_type_router.py    # Выбор типа колонки
│   │   │   │       ├── settings_router.py       # Настройки загрузки
│   │   │   │       └── template_router.py       # Шаблоны колонок
│   │   │   ├── user/                   # 🆕 Пользовательские обработчики
│   │   │   │   ├── __init__.py
│   │   │   │   ├── basic_handlers.py            # /start, основные команды
│   │   │   │   ├── help_handlers.py             # /help, справка
│   │   │   │   ├── hint_handlers.py             # /hint, информация о подсказках
│   │   │   │   ├── settings_handlers.py         # /settings + индивидуальные настройки
│   │   │   │   └── stats_handlers.py            # /stats, статистика
│   │   │   └── study/                  # 🆕 Обработчики изучения слов
│   │   │       ├── __init__.py
│   │   │       ├── study_commands.py            # /study, команды изучения
│   │   │       ├── study_words.py               # Отображение слов, batch-загрузка
│   │   │       ├── study_word_actions.py        # 🆕 Роутер для действий со словами
│   │   │       ├── study_hint_handlers.py       # Роутер для подсказок
│   │   │       ├── hint/                        # 🆕 Обработчики подсказок
│   │   │       │   ├── __init__.py
│   │   │       │   ├── common.py                # Общие функции, отмена операций
│   │   │       │   ├── create_handlers.py       # Создание подсказок + голос
│   │   │       │   ├── edit_handlers.py         # Редактирование подсказок
│   │   │       │   ├── toggle_handlers.py       # Переключение видимости
│   │   │       │   └── unknown.py               # Обработка неожиданных сообщений
│   │   │       └── word_actions/               # 🆕 Детализированные действия
│   │   │           ├── __init__.py
│   │   │           ├── word_display_actions.py  # Показ слов, изображений
│   │   │           ├── word_evaluation_actions.py # Оценка слов (знаю/не знаю)
│   │   │           ├── word_navigation_actions.py # Навигация между словами + batch-загрузка
│   │   │           └── word_utility_actions.py   # Утилитарные действия
│   │   ├── keyboards/                           # 🆕 ОБНОВЛЕНЫ: Все клавиатуры
│   │   │   ├── __init__.py
│   │   │   ├── admin_keyboards.py      # 🆕 Админ-клавиатуры + специальные для изучения
│   │   │   ├── user_keyboards.py       # Пользовательские клавиатуры
│   │   │   ├── inline_keyboards.py     # Базовые inline-клавиатуры
│   │   │   └── study_keyboards.py      # 🆕 Клавиатуры изучения + изображения + админ-кнопки
│   │   └── middleware/
│   │       ├── __init__.py
│   │       └── auth_middleware.py      # 🆕 РАСШИРЕНО: Промежуточное ПО с meta-состояниями
│   ├── api/
│   │   ├── __init__.py
│   │   ├── client.py                   # API клиент для бэкенда
│   │   └── models/
│   │       ├── __init__.py
│   │       ├── language.py             # Модели данных для языков
│   │       ├── user.py                 # Модели данных для пользователей
│   │       └── word.py                 # Модели данных для слов
│   └── utils/                          # 🆕 ЗНАЧИТЕЛЬНО РАСШИРЕНЫ
│       ├── __init__.py
│       ├── admin_utils.py              # 🆕 НОВЫЙ: Утилиты для проверки прав админа
│       ├── api_utils.py                # Утилиты для работы с API + клиент
│       ├── audio_utils.py              # Утилиты для работы с аудио
│       ├── callback_constants.py       # 🆕 ОБНОВЛЕНО: Константы + изображения + админ
│       ├── error_utils.py              # 🆕 РАСШИРЕНО: Обработка ошибок + meta-состояния
│       ├── ffmpeg_utils.py             # 🆕 НОВЫЙ: Утилиты для FFmpeg
│       ├── file_utils.py               # Утилиты для работы с файлами
│       ├── formatting_utils.py         # 🆕 ОБНОВЛЕНО: Форматирование + изображения
│       ├── hint_constants.py           # 🆕 РАСШИРЕНО: Константы + индивидуальные настройки
│       ├── hint_settings_utils.py      # 🆕 НОВЫЙ: Индивидуальные настройки подсказок
│       ├── logger.py                   # Настройка логирования
│       ├── settings_utils.py           # 🆕 ОБНОВЛЕНО: Настройки + индивидуальные подсказки
│       ├── state_models.py             # 🆕 РАСШИРЕНО: Модели состояний + batch-loading
│       ├── user_utils.py               # 🆕 НОВЫЙ: Утилиты для работы с пользователями
│       ├── voice_recognition.py        # Утилиты для распознавания речи
│       ├── voice_utils.py              # 🆕 НОВЫЙ: Обработка голосовых сообщений
│       ├── word_data_utils.py          # Утилиты для данных слов
│       └── word_image_generator.py     # 🆕 НОВЫЙ: Генератор изображений с Unicode
├── conf/
│   ├── __init__.py
│   └── config/
│       ├── __init__.py
│       ├── default.yaml                # Основной файл конфигурации
│       ├── bot.yaml                    # 🆕 ОБНОВЛЕНО: Настройки + конфигурация изображений
│       ├── api.yaml                    # Настройки API клиента
│       ├── logging.yaml                # Настройки логирования
│       └── learning.yaml               # Настройки обучения
├── logs/
│   └── app.log                         # Файл логов фронтенда
├── tests/                              # 🆕 РАСШИРЕНЫ: Новые тесты
│   ├── __init__.py
│   ├── conftest.py                     # Конфигурация pytest
│   ├── test_main.py                    # Тесты главного модуля
│   ├── test_bot_commands.py            # Тесты команд бота
│   ├── bot_test_framework/             # Фреймворк для тестирования бота
│   │   ├── __init__.py
│   │   ├── bot_actions.py              # Классы действий
│   │   ├── bot_test_context.py         # Контекст тестирования
│   │   ├── command_handler.py          # Обработчик команд
│   │   ├── message_handler.py          # Обработчик сообщений
│   │   ├── callback_handler.py         # Обработчик callback
│   │   ├── bot_test_scenario.py        # Класс сценария
│   │   ├── bot_test_framework.py       # Основной модуль
│   │   └── scenario_executor.py        # Исполнитель сценариев
│   ├── test_scenarios/                 # Тесты сценариев
│   │   ├── __init__.py
│   │   ├── test_user_scenario.py       # Тесты пользователя
│   │   └── scenarios/                  # YAML-файлы сценариев
│   │       ├── start_help_settings.yaml
│   │       └── settings_toggle.yaml
│   ├── test_handlers/                  # Тесты обработчиков
│   │   ├── test_user/                   # Тесты пользовательских обработчиков
│   │   │   ├── test_user_handlers.py       # Тесты основных обработчиков
│   │   │   ├── test_basic_handlers.py      # Тесты базовых команд
│   │   │   ├── test_help_handlers.py       # Тесты справки
│   │   │   ├── test_settings_handlers.py   # Тесты настроек
│   │   │   └── test_stats_handlers.py      # Тесты статистики
│   │   └── test_admin/                  # Тесты админ-обработчиков
│   │       ├── test_admin_basic_handlers.py    # Тесты базовых админ-команд
│   │       ├── test_admin_language_handlers.py # Тесты управления языками
│   │       ├── test_admin_upload_handlers.py   # Тесты загрузки файлов
│   │       ├── test_admin_upload_column_handlers.py # Тесты настройки колонок
│   │       ├── test_admin_upload_routers.py    # Тесты роутеров загрузки
│   │       └── test_admin_word_handlers.py     # 🆕 Тесты админ-редактирования слов
│   ├── test_utils/                     # 🆕 НОВЫЕ: Тесты утилит
│   │   ├── test_admin_utils.py         # 🆕 Тесты утилит администратора
│   │   ├── test_callback_constants.py  # 🆕 Тесты констант callback
│   │   ├── test_centralized_states.py  # 🆕 Тесты централизованных состояний
│   │   ├── test_voice_utils.py         # 🆕 Тесты голосовых утилит
│   │   └── test_word_image_generator.py # 🆕 Тесты генератора изображений
│   └── test_api/                       # Тесты API клиента
└── watch_and_reload.py                 # Скрипт автоперезапуска
```

## Бэкенд (REST API)

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py               # Точка входа бэкенда
│   ├── api/
│   │   ├── __init__.py
│   │   ├── routes/
│   │   │   ├── __init__.py
│   │   │   ├── languages.py           # Эндпоинты для языков
│   │   │   ├── users.py               # Эндпоинты для пользователей
│   │   │   ├── words.py               # Эндпоинты для слов
│   │   │   └── statistics.py          # Эндпоинты для статистики
│   │   ├── schemas/
│   │   │   ├── __init__.py
│   │   │   ├── language.py            # Схемы данных для языков
│   │   │   ├── user.py                # Схемы данных для пользователей
│   │   │   ├── word.py                # Схемы данных для слов
│   │   │   └── statistics.py          # Схемы данных для статистики
│   ├── db/
│   │   ├── __init__.py
│   │   ├── database.py               # Конфигурация MongoDB
│   │   ├── repositories/
│   │   │   ├── __init__.py
│   │   │   ├── base_repository.py    # Базовый репозиторий
│   │   │   ├── language_repository.py # Репозиторий языков
│   │   │   ├── user_repository.py     # Репозиторий пользователей
│   │   │   ├── word_repository.py     # Репозиторий слов
│   │   │   └── statistics_repository.py # Репозиторий статистики
│   ├── services/
│   │   ├── __init__.py
│   │   ├── language_service.py       # Сервис для языков
│   │   ├── user_service.py           # Сервис для пользователей
│   │   ├── word_service.py           # Сервис для слов
│   │   ├── statistics_service.py     # Сервис для статистики
│   │   └── excel_service.py          # Сервис для Excel
│   ├── core/
│   │   ├── __init__.py
│   │   ├── dependencies.py           # Зависимости FastAPI
│   │   └── exceptions.py             # Пользовательские исключения
│   └── utils/
│       ├── __init__.py
│       └── logger.py                 # Настройка логирования
├── conf/
│   ├── __init__.py
│   └── config/
│       ├── __init__.py
│       ├── default.yaml              # Основной файл конфигурации
│       ├── api.yaml                  # Настройки API сервера
│       ├── database.yaml             # Настройки MongoDB
│       └── logging.yaml              # Настройки логирования
├── logs/
│   └── backend.log                   # Файл логов бэкенда
└── tests/
    ├── __init__.py
    ├── conftest.py                   # Конфигурация pytest
    ├── test_api/                     # Тесты API
    ├── test_services/                # Тесты сервисов
    └── test_repositories/            # Тесты репозиториев
```

## Общие модули (Common)

```
common/
├── __init__.py
├── utils/
│   ├── __init__.py
│   ├── logger.py             # Унифицированный модуль логирования
│   └── [другие утилиты]      # Другие общие утилиты
└── tests/
    ├── __init__.py
    ├── conftest.py           # Конфигурация pytest для модуля common
    └── test_utils_logger.py  # Тесты для logger.py
```

## Служебные скрипты

```
scripts/
├── __init__.py
├── init_db.py                # Инициализация БД
├── seed_data.py              # Заполнение тестовыми данными
├── run_tests.py              # Запуск тестов
├── migrate_data.py           # Миграция данных
├── admin_manager.py          # Управление администраторами
└── create_user_language_settings_collection.py  # Создание коллекции настроек
```
