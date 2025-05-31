Структура каталогов и файлов проекта (обновлено с изображениями слов и админ-редактированием из изучения)
Содержание

Корневой каталог
Каталог документации
Фронтенд (Telegram-бот)
Бэкенд (REST API)
Служебные скрипты
Обновления архитектуры

Корневой каталог
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

Каталог документации
docs/
├── README.md                    # Обзор документации
├── summary.md                   # Структура документации
│
├── architecture.md              # 🆕 ОБНОВЛЕНО: Архитектура с Meta-состояниями
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
    ├── bot_commands.md          # 🆕 ОБНОВЛЕНО: Команды и действия бота (с изображениями и админ-редактированием)
    ├── admin_tools.md           # Инструменты администрирования
    └── learning_system.md       # 🆕 ОБНОВЛЕНО: Система изучения слов (с изображениями)
    
Фронтенд (Telegram-бот)
frontend/
├── app/
│   ├── __init__.py
│   ├── main_frontend.py      # Точка входа фронтенда
│   ├── bot/
│   │   ├── __init__.py
│   │   ├── bot.py            # Основной класс бота
│   │   ├── states/           # ОБНОВЛЕНО: Централизованные состояния FSM
│   │   │   ├── __init__.py
│   │   │   └── centralized_states.py    # 🆕 ОБНОВЛЕНО: Все состояния FSM + viewing_word_image
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
│   │   │   │   └── admin_word_handlers.py      # 🆕 ОБНОВЛЕНО: Управление словами + переходы из изучения
│   │   │   ├── user/                # Подмодули пользователя
│   │   │   │   ├── __init__.py
│   │   │   │   ├── basic_handlers.py      # Базовые команды пользователя
│   │   │   │   ├── help_handlers.py       # Команда /help
│   │   │   │   ├── hint_handlers.py       # Команда /hint
│   │   │   │   ├── settings_handlers.py   # Команда /settings (ОБНОВЛЕН)
│   │   │   │   └── stats_handlers.py      # Команда /stats
│   │   │   └── study/                  # Подмодули изучения слов
│   │   │       ├── __init__.py
│   │   │       ├── study_commands.py         # Команда /study
│   │   │       ├── study_words.py            # 🆕 ОБНОВЛЕНО: Получение и отображение слов + админ-проверки
│   │   │       ├── study_word_actions.py     # 🆕 ОБНОВЛЕНО: Действия со словами + изображения + админ-редактирование
│   │   │       ├── study_hint_handlers.py    # Регистрация обработчиков подсказок
│   │   │       └── hint/                     # Подмодули подсказок (ВСЕ ОБНОВЛЕНЫ)
│   │   │           ├── __init__.py
│   │   │           ├── common.py             # Общие функции и отмена
│   │   │           ├── create_handlers.py    # Создание подсказок (РЕФАКТОРИНГ)
│   │   │           ├── edit_handlers.py      # Редактирование подсказок (РЕФАКТОРИНГ)
│   │   │           ├── view_handlers.py      # Просмотр подсказок
│   │   │           └── toggle_handlers.py    # Переключение видимости (РЕФАКТОРИНГ)
│   │   ├── keyboards/                       # 🆕 ОБНОВЛЕНЫ: ВСЕ ФАЙЛЫ с поддержкой изображений и админ-кнопок
│   │   │   ├── __init__.py
│   │   │   ├── admin_keyboards.py      # 🆕 ОБНОВЛЕНО: Клавиатуры для администратора + специальные для изучения
│   │   │   ├── user_keyboards.py       # Клавиатуры для пользователя (РЕФАКТОРИНГ)
│   │   │   ├── inline_keyboards.py     # Базовые inline-клавиатуры
│   │   │   └── study_keyboards.py      # 🆕 ОБНОВЛЕНО: Клавиатуры для изучения + кнопки изображений + админ-кнопки
│   │   └── middleware/
│   │       ├── __init__.py
│   │       └── auth_middleware.py      # Промежуточное ПО для авторизации (УЛУЧШЕНО)
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
│       ├── api_utils.py                # 🆕 ОБНОВЛЕНО: Утилиты для работы с API + хранение клиента
│       ├── formatting_utils.py         # 🆕 ОБНОВЛЕНО: Утилиты форматирования + ссылки на изображения
│       ├── error_utils.py              # Утилиты для обработки ошибок
│       ├── settings_utils.py           # Утилиты для настроек
│       ├── state_models.py             # Модели для работы с FSM
│       ├── word_data_utils.py          # Утилиты для данных слов
│       ├── hint_constants.py           # Константы для подсказок
│       ├── callback_constants.py       # 🆕 ОБНОВЛЕНО: Константы callback_data + изображения + админ-редактирование
│       ├── voice_utils.py              # НОВОЕ: Утилиты для голосовых сообщений
│       ├── voice_recognition.py        # Утилиты для распознавания речи
│       ├── audio_utils.py              # Утилиты для работы с аудио
│       ├── ffmpeg_utils.py             # Утилиты для FFmpeg
│       ├── hint_settings_utils.py      # Утилиты для индивидуальных настроек подсказок
│       ├── word_image_generator.py     # 🆕 НОВЫЙ: Генератор изображений слов с Unicode поддержкой
│       └── admin_utils.py              # 🆕 НОВЫЙ: Утилиты для проверки прав администратора
├── conf/
│   ├── __init__.py
│   └── config/
│       ├── __init__.py
│       ├── default.yaml                # Основной файл конфигурации
│       ├── bot.yaml                    # 🆕 ОБНОВЛЕНО: Настройки бота + конфигурация изображений
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
│   │   ├── test_user/                   # Тесты обработчиков пользователя
│   │   │   ├── test_user_handlers.py       # Тесты основных обработчиков пользователя
│   │   │   └── [другие тесты пользовательских обработчиков]
│   │   └── test_admin/                  # Тесты обработчиков администратора
│   │       ├── test_admin_basic_handlers.py    # Тесты базовых обработчиков администратора
│   │       ├── test_admin_language_handlers.py # Тесты обработчиков управления языками
│   │       ├── test_admin_upload_handlers.py   # Тесты обработчиков загрузки файлов
│   │       ├── test_admin_upload_column_handlers.py   # Тесты обработчиков настройки колонок
│   │       ├── test_admin_upload_routers.py    # Тесты структуры роутеров загрузки
│   │       └── test_admin_word_handlers.py     # 🆕 НОВЫЙ: Тесты админ-редактирования слов
│   ├── test_utils/                     # Тесты утилит
│   │   ├── test_callback_constants.py  # НОВОЕ: Тесты констант callback
│   │   ├── test_voice_utils.py         # НОВОЕ: Тесты голосовых утилит
│   │   ├── test_centralized_states.py  # НОВОЕ: Тесты централизованных состояний
│   │   ├── test_word_image_generator.py # 🆕 НОВЫЙ: Тесты генератора изображений
│   │   └── test_admin_utils.py         # 🆕 НОВЫЙ: Тесты утилит администратора
│   └── test_api/                       # Тесты API клиента
└── watch_and_reload.py                 # Скрипт автоперезапуска

Бэкенд (REST API)
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

Общие модули (Common)
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

Служебные скрипты
scripts/
├── __init__.py
├── init_db.py                # Инициализация БД
├── seed_data.py              # Заполнение тестовыми данными
├── run_tests.py              # Запуск тестов
├── migrate_data.py           # Миграция данных
├── admin_manager.py          # Управление администраторами
└── create_user_language_settings_collection.py  # Создание коллекции настроек

