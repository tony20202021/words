# Команды и действия бота (обновлено с системой генерации изображений)

## Содержание

1. [Основные команды пользователя](#основные-команды-пользователя)
2. [Административные команды](#административные-команды)
3. [Системные команды](#системные-команды)
4. [Действия пользователя](#действия-пользователя)
5. [Индивидуальные настройки подсказок](#индивидуальные-настройки-подсказок)
6. [Система генерации изображений слов](#система-генерации-изображений-слов)
7. [Meta-состояния и обработка ошибок](#meta-состояния-и-обработка-ошибок)
8. [Структура обработчиков](#структура-обработчиков)

## Основные команды пользователя

| Команда | Описание | Обработчик | Файл |
|---------|----------|------------|------|
| `/start` | Начать работу с ботом, отображение приветствия | `cmd_start` | `user/basic_handlers.py` |
| `/help` | Получить справку по работе с ботом | `cmd_help` | `user/help_handlers.py` |
| `/language` | Выбрать язык для изучения | `cmd_language` | `language_handlers.py` |
| `/settings` | Настройки процесса обучения | `cmd_settings` | `user/settings_handlers.py` |
| `/study` | Начать изучение слов | `cmd_study` | `study/study_commands.py` |
| `/stats` | Показать статистику изучения | `cmd_stats` | `user/stats_handlers.py` |
| `/hint` | Информация о подсказках | `cmd_hint` | `user/hint_handlers.py` |
| `/show_big` | **Показать крупное изображение слова с автоподбором размера шрифта** | `cmd_show_big_word` | `study/study_word_actions.py` |
| `/cancel` | Отмена текущего действия | `cmd_cancel_universal` | `user/cancel_handlers.py` |

## Административные команды

| Команда | Описание | Обработчик | Файл |
|---------|----------|------------|------|
| `/admin` | Вход в административную панель | `cmd_admin` | `admin/admin_basic_handlers.py` |
| `/managelang` | Управление языками | `cmd_manage_languages` | `admin/admin_language_handlers.py` |
| `/upload` | Загрузка файла со словами | `cmd_upload` | `admin/admin_upload_handlers.py` |
| `/admin_stats` | Административная статистика | `cmd_admin_stats` | `admin/admin_basic_handlers.py` |

## Системные команды

| Команда | Описание | Обработчик | Файл |
|---------|----------|------------|------|
| `/retry` | Повторить действие после ошибки | `cmd_retry` | `common_handlers.py` |
| `/status` | Показать статус системы | `cmd_status` | `common_handlers.py` |

## Действия пользователя

### Выбор языка

| Действие | Описание | Обработчик | Callback Constant |
|----------|----------|------------|-------------------|
| `lang_select_*` | Выбор языка для изучения | `process_language_selection` | `CallbackData.LANG_SELECT_TEMPLATE` |

### Настройки обучения

| Действие | Описание | Обработчик | Callback Constant |
|----------|----------|------------|-------------------|
| `settings_start_word` | Изменение стартового слова | `process_settings_start_word` | `CallbackData.SETTINGS_START_WORD` |
| `settings_toggle_skip_marked` | Переключение пропуска помеченных слов | `process_toggle_skip_marked` | `CallbackData.SETTINGS_TOGGLE_SKIP_MARKED` |
| `settings_toggle_check_date` | Переключение учета даты проверки | `process_toggle_check_date` | `CallbackData.SETTINGS_TOGGLE_CHECK_DATE` |
| `settings_toggle_show_debug` | Переключение отладочной информации | `process_toggle_show_debug` | `CallbackData.SETTINGS_TOGGLE_SHOW_DEBUG` |

### Процесс изучения слов

| Действие | Описание | Обработчик | Callback Constant |
|----------|----------|------------|-------------------|
| `word_know` | Отметить слово как известное | `process_word_know` | `CallbackData.WORD_KNOW` |
| `word_dont_know` | Отметить слово как неизвестное | `process_word_dont_know` | `CallbackData.WORD_DONT_KNOW` |
| `show_word` | Показать слово на изучаемом языке | `process_show_word` | `CallbackData.SHOW_WORD` |
| `next_word` | Перейти к следующему слову | `process_next_word` | `CallbackData.NEXT_WORD` |
| `confirm_next_word` | Подтвердить переход к следующему слову | `process_confirm_next_word` | `CallbackData.CONFIRM_NEXT_WORD` |
| `toggle_word_skip` | Переключить флаг пропуска слова | `process_toggle_word_skip` | `CallbackData.TOGGLE_WORD_SKIP` |

## Индивидуальные настройки подсказок

**Каждый тип подсказки настраивается индивидуально через `/settings`.**

### Типы настроек подсказок

| Настройка | Описание | Callback Constant |
|-----------|----------|-------------------|
| `show_hint_meaning` | Ассоциации на русском | `CallbackData.SETTINGS_TOGGLE_HINT_MEANING` |
| `show_hint_phoneticassociation` | Фонетические ассоциации | `CallbackData.SETTINGS_TOGGLE_HINT_PHONETICASSOCIATION` |
| `show_hint_phoneticsound` | Звучание по слогам | `CallbackData.SETTINGS_TOGGLE_HINT_PHONETICSOUND` |
| `show_hint_writing` | Подсказки написания | `CallbackData.SETTINGS_TOGGLE_HINT_WRITING` |

### Работа с индивидуальными подсказками

| Действие | Описание | Обработчик | Callback Generator |
|----------|----------|------------|-------------------|
| `hint_view_*` | Показать подсказку для слова | `process_hint_view` | `format_hint_callback("view", ...)` |
| `hint_create_*` | Добавить новую подсказку | `process_hint_create` | `format_hint_callback("create", ...)` |
| `hint_edit_*` | Редактировать существующую подсказку | `process_hint_edit` | `format_hint_callback("edit", ...)` |
| `hint_toggle_*` | Переключить видимость подсказки | `process_hint_toggle` | `format_hint_callback("toggle", ...)` |

### Bulk операции с подсказками

| Действие | Описание | Обработчик |
|----------|----------|------------|
| `enable_all_hints` | Включить все типы подсказок | `process_enable_all_hints` |
| `disable_all_hints` | Отключить все типы подсказок | `process_disable_all_hints` |

## Система генерации изображений слов

### Команды и действия для работы с изображениями

| Действие | Описание | Обработчик | Константа/Команда |
|----------|----------|------------|-------------------|
| **Команда `/show_big`** | Показать крупное изображение текущего слова | `cmd_show_big_word` | `/show_big` |
| **Кнопка "Показать крупное написание"** | Показать изображение через кнопку интерфейса | `process_show_word_image_callback` | `CallbackData.SHOW_WORD_IMAGE` |
| **Кнопка "Вернуться к слову"** | Вернуться от изображения к экрану изучения | `process_back_from_image` | `CallbackData.BACK_FROM_IMAGE` |

### Состояния для работы с изображениями

| Состояние | Описание |
|-----------|----------|
| `StudyStates.viewing_word_image` | Просмотр крупного изображения слова |

## Meta-состояния и обработка ошибок

**Система автоматически переходит в специальные состояния при системных ошибках.**

### CommonStates (Meta-состояния)

| Состояние | Описание | Обработчик |
|-----------|----------|------------|
| `handling_api_error` | Обработка ошибки API | `handle_api_error_state` |
| `connection_lost` | Потеря соединения с сервером | `handle_connection_lost_state` |
| `unknown_command` | Обработка неизвестной команды | `handle_unknown_command_state` |

### Автоматическое восстановление

Система автоматически:
- Переходит в meta-состояния при ошибках
- Пытается восстановить соединение
- Предлагает пользователю варианты восстановления
- Сохраняет важные данные сессии

## Структура обработчиков

### Приоритеты обработчиков

1. **common_handlers** (приоритет: самый высокий)
   - Meta-состояния и системные ошибки
   - Команды `/retry`, `/status`

2. **user_handlers** (приоритет: высокий)
   - Основные пользовательские команды

3. **admin_handlers** (приоритет: средний)
   - Административные команды
   - Управление системой

4. **language_handlers** (приоритет: низкий)
   - Выбор языка изучения

5. **study_handlers** (приоритет: низкий)
   - Процесс изучения слов

6. **cancel_handlers** (приоритеты: 100)
   - Универсальный обработчик `/cancel`
   - Обработка неожиданных сообщений в состояниях
