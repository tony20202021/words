# Структура каталогов и файлов проекта

## Содержание
1. [Корневой каталог](#корневой-каталог)
2. [Каталог документации](#каталог-документации)
3. [Фронтенд (Telegram-бот)](#фронтенд-telegram-бот)
4. [Бэкенд (REST API)](#бэкенд-rest-api)
5. [Служебные скрипты](#служебные-скрипты)

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
└── scripts/                  # Каталог со служебными скриптами
```

## Каталог документации

```
docs/
├── README.md                    # Обзор документации
├── summary.md                   # Структура документации
│
├── architecture.md              # Архитектура проекта
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
│   └── directory_structure.md   # Структура каталогов (этот файл)
│
└── functionality/               # Функциональность бота
    ├── bot_commands.md          # Команды и действия бота
    ├── admin_tools.md           # Инструменты администрирования
    └── learning_system.md       # Система изучения слов
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
│   │   ├── handlers/
│   │   │   ├── __init__.py
│   │   │   ├── admin_handlers.py     # Объединяет обработчики админа
│   │   │   ├── user_handlers.py      # Объединяет обработчики пользователя
│   │   │   ├── language_handlers.py  # Обработчики выбора языка
│   │   │   ├── study_handlers.py     # Объединяет обработчики изучения
│   │   │   ├── admin/               # Подмодули администратора
│   │   │   │   ├── __init__.py
│   │   │   │   ├── admin_basic_handlers.py     # Базовые команды админа
│   │   │   │   ├── admin_language_handlers.py  # Управление языками
│   │   │   │   ├── admin_upload_handlers.py    # Загрузка файлов
│   │   │   │   └── admin_states.py             # Состояния FSM админа
│   │   │   ├── user/                # Подмодули пользователя
│   │   │   │   ├── __init__.py
│   │   │   │   ├── basic_handlers.py      # Базовые команды пользователя
│   │   │   │   ├── help_handlers.py       # Команда /help
│   │   │   │   ├── hint_handlers.py       # Команда /hint
│   │   │   │   ├── settings_handlers.py   # Команда /settings
│   │   │   │   └── stats_handlers.py      # Команда /stats
│   │   │   └── study/                  # Подмодули изучения слов
│   │   │       ├── __init__.py
│   │   │       ├── study_states.py           # Состояния FSM изучения
│   │   │       ├── study_commands.py         # Команда /study
│   │   │       ├── study_words.py            # Получение и отображение слов
│   │   │       ├── study_word_actions.py     # Действия со словами
│   │   │       ├── study_hint_handlers.py    # Регистрация обработчиков подсказок
│   │   │       └── hint/                     # Подмодули подсказок
│   │   │           ├── __init__.py
│   │   │           ├── common.py             # Общие функции и отмена
│   │   │           ├── create_handlers.py    # Создание подсказок
│   │   │           ├── edit_handlers.py      # Редактирование подсказок
│   │   │           ├── view_handlers.py      # Просмотр подсказок
│   │   │           └── toggle_handlers.py    # Переключение видимости
│   │   ├── keyboards/
│   │   │   ├── __init__.py
│   │   │   ├── admin_keyboards.py      # Клавиатуры для администратора
│   │   │   ├── user_keyboards.py       # Клавиатуры для пользователя
│   │   │   ├── inline_keyboards.py     # Базовые inline-клавиатуры
│   │   │   └── study_keyboards.py      # Клавиатуры для изучения
│   │   ├── states/
│   │   │   ├── __init__.py
│   │   │   ├── admin_states.py         # Состояния FSM администратора
│   │   │   └── user_states.py          # Состояния FSM пользователя
│   │   └── middleware/
│   │       ├── __init__.py
│   │       └── auth_middleware.py      # Промежуточное ПО для авторизации
│   ├── api/
│   │   ├── __init__.py
│   │   ├── client.py                   # API клиент для бэкенда
│   │   └── models/
│   │       ├── __init__.py
│   │       ├── language.py             # Модели данных для языков
│   │       ├── user.py                 # Модели данных для пользователей
│   │       └── word.py                 # Модели данных для слов
│   └── utils/
│       ├── __init__.py
│       ├── logger.py                   # Настройка логирования
│       ├── file_utils.py               # Утилиты для работы с файлами
│       ├── api_utils.py                # Утилиты для работы с API
│       ├── formatting_utils.py         # Утилиты для форматирования
│       ├── error_utils.py              # Утилиты для обработки ошибок
│       ├── settings_utils.py           # Утилиты для настроек
│       ├── state_models.py             # Модели для работы с FSM
│       ├── word_data_utils.py          # Утилиты для данных слов
│       └── hint_constants.py           # Константы для подсказок
├── conf/
│   ├── __init__.py
│   └── config/
│       ├── __init__.py
│       ├── default.yaml                # Основной файл конфигурации
│       ├── bot.yaml                    # Настройки бота
│       ├── api.yaml                    # Настройки API клиента
│       ├── logging.yaml                # Настройки логирования
│       └── learning.yaml               # Настройки обучения
├── logs/
│   └── app.log                         # Файл логов фронтенда
├── tests/
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
│   ├── test_utils/                     # Тесты утилит
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