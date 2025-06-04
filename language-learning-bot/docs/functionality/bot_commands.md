# Команды и действия бота (ОБНОВЛЕНО v1.4.1)

## Содержание

1. [Основные команды пользователя](#основные-команды-пользователя)
2. [Административные команды](#административные-команды)
3. [Системные команды](#системные-команды)
4. [Действия пользователя](#действия-пользователя)
5. [Индивидуальные настройки подсказок](#индивидуальные-настройки-подсказок)
6. [Система генерации изображений слов](#система-генерации-изображений-слов)
7. [Админ-редактирование из режима изучения](#админ-редактирование-из-режима-изучения)
8. [Система batch-загрузки слов](#система-batch-загрузки-слов)
9. [Meta-состояния и обработка ошибок](#meta-состояния-и-обработка-ошибок)
10. [Голосовые подсказки](#голосовые-подсказки)
11. [Структура обработчиков](#структура-обработчиков)

## Основные команды пользователя

| Команда | Описание | Обработчик | Файл |
|---------|----------|------------|------|
| `/start` | Начать работу с ботом, отображение приветствия | `cmd_start` | `user/basic_handlers.py` |
| `/help` | Получить справку по работе с ботом | `cmd_help` | `user/help_handlers.py` |
| `/language` | Выбрать язык для изучения | `cmd_language` | `language_handlers.py` |
| `/settings` | Настройки процесса обучения и индивидуальные настройки подсказок | `cmd_settings` | `user/settings_handlers.py` |
| `/study` | Начать изучение слов с batch-загрузкой | `cmd_study` | `study/study_commands.py` |
| `/stats` | Показать статистику изучения | `cmd_stats` | `user/stats_handlers.py` |
| `/hint` | Информация о подсказках | `cmd_hint` | `user/hint_handlers.py` |
| `/show_big` | **🆕 Показать крупное изображение текущего слова с Unicode поддержкой** | `cmd_show_big_word` | `study/word_actions/word_display_actions.py` |
| `/cancel` | Отмена текущего действия | `cmd_cancel_universal` | `user/cancel_handlers.py` |

## Административные команды

| Команда | Описание | Обработчик | Файл |
|---------|----------|------------|------|
| `/admin` | Вход в административную панель | `cmd_admin` | `admin/admin_basic_handlers.py` |
| `/managelang` | Управление языками | `cmd_manage_languages` | `admin/admin_language_handlers.py` |
| `/upload` | Загрузка файла со словами | `cmd_upload` | `admin/file_upload/file_router.py` |
| `/bot_stats` | Административная статистика | `cmd_bot_stats` | `admin/admin_basic_handlers.py` |
| `/users` | **🆕 Управление пользователями** | `cmd_manage_users` | `admin/admin_basic_handlers.py` |

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

| Действие | Описание | Обработчик | Callback Constant | Файл |
|----------|----------|------------|-------------------|------|
| `word_know` | Отметить слово как известное | `process_word_know` | `CallbackData.WORD_KNOW` | `study/word_actions/word_evaluation_actions.py` |
| `word_dont_know` | Отметить слово как неизвестное | `process_word_dont_know` | `CallbackData.WORD_DONT_KNOW` | `study/word_actions/word_evaluation_actions.py` |
| `show_word` | Показать слово на изучаемом языке | `process_show_word` | `CallbackData.SHOW_WORD` | `study/word_actions/word_display_actions.py` |
| `next_word` | **🆕 Перейти к следующему слову с автоматической batch-загрузкой** | `process_next_word` | `CallbackData.NEXT_WORD` | `study/word_actions/word_navigation_actions.py` |
| `confirm_next_word` | Подтвердить переход к следующему слову | `process_confirm_next_word` | `CallbackData.CONFIRM_NEXT_WORD` | `study/word_actions/word_navigation_actions.py` |
| `toggle_word_skip` | Переключить флаг пропуска слова | `process_toggle_word_skip` | `CallbackData.TOGGLE_WORD_SKIP` | `study/word_actions/word_utility_actions.py` |

## Индивидуальные настройки подсказок

**🆕 Каждый тип подсказки настраивается индивидуально через `/settings`.**

### Типы настроек подсказок

| Настройка | Описание | Callback Constant | Обработчик |
|-----------|----------|-------------------|------------|
| `show_hint_meaning` | Ассоциации на русском | `CallbackData.SETTINGS_TOGGLE_HINT_MEANING` | `process_hint_setting_toggle` |
| `show_hint_phoneticassociation` | Фонетические ассоциации | `CallbackData.SETTINGS_TOGGLE_HINT_PHONETICASSOCIATION` | `process_hint_setting_toggle` |
| `show_hint_phoneticsound` | Звучание по слогам | `CallbackData.SETTINGS_TOGGLE_HINT_PHONETICSOUND` | `process_hint_setting_toggle` |
| `show_hint_writing` | Подсказки написания | `CallbackData.SETTINGS_TOGGLE_HINT_WRITING` | `process_hint_setting_toggle` |

### Работа с индивидуальными подсказками

| Действие | Описание | Обработчик | Callback Generator | Файл |
|----------|----------|------------|-------------------|------|
| `hint_view_*` | Показать подсказку для слова | `process_hint_toggle` | `format_hint_callback("toggle", ...)` | `study/hint/toggle_handlers.py` |
| `hint_create_*` | Добавить новую подсказку | `process_hint_create` | `format_hint_callback("create", ...)` | `study/hint/create_handlers.py` |
| `hint_edit_*` | Редактировать существующую подсказку | `process_hint_edit` | `format_hint_callback("edit", ...)` | `study/hint/edit_handlers.py` |

### Bulk операции с подсказками

| Действие | Описание | Обработчик | Файл |
|----------|----------|------------|------|
| `enable_all_hints` | Включить все типы подсказок | `process_enable_all_hints` | `user/settings_handlers.py` |
| `disable_all_hints` | Отключить все типы подсказок | `process_disable_all_hints` | `user/settings_handlers.py` |

## Система генерации изображений слов

### 🆕 Команды и действия для работы с изображениями

| Действие | Описание | Обработчик | Константа/Команда | Файл |
|----------|----------|------------|-------------------|------|
| **Команда `/show_big`** | Показать крупное изображение текущего слова | `cmd_show_big_word` | `/show_big` | `study/word_actions/word_display_actions.py` |
| **Кнопка "🔍 Показать крупное написание"** | Показать изображение через кнопку интерфейса | `process_show_word_image_callback` | `CallbackData.SHOW_WORD_IMAGE` | `study/word_actions/word_display_actions.py` |
| **Кнопка "⬅️ Вернуться к слову"** | Вернуться от изображения к экрану изучения | `process_back_from_image` | `CallbackData.BACK_FROM_IMAGE` | `study/word_actions/word_display_actions.py` |

### Особенности системы изображений

- **Unicode поддержка** - работает с китайскими иероглифами, арабским, хинди и другими письменностями
- **Автоподбор размера шрифта** - если текст не помещается, размер автоматически уменьшается
- **Умное позиционирование** - центрирование по горизонтали и вертикали
- **Настраиваемый дизайн** - через конфигурацию в `bot.yaml`

### Состояния для работы с изображениями

| Состояние | Описание |
|-----------|----------|
| `StudyStates.viewing_word_image` | Просмотр крупного изображения слова |

## Админ-редактирование из режима изучения

**🆕 НОВАЯ ФУНКЦИОНАЛЬНОСТЬ**: Администраторы могут редактировать слова прямо из экрана изучения без перехода в админ-панель.

### Команды и действия для админ-редактирования

| Действие | Описание | Обработчик | Константа/Доступ | Файл |
|----------|----------|------------|------------------|------|
| **Кнопка "✏️ Редактировать слово"** | Переход к редактированию слова из изучения | `process_edit_word_from_study` | `CallbackData.ADMIN_EDIT_WORD_FROM_STUDY` | `admin/admin_word_handlers.py` |
| **Кнопка "⬅️ Вернуться к изучению"** | Возврат из админ-режима к изучению | `process_back_to_study_from_admin` | `CallbackData.BACK_TO_STUDY_FROM_ADMIN` | `study/word_actions/word_navigation_actions.py` |

### Проверка прав администратора

| Функция | Описание | Файл |
|---------|----------|------|
| `is_user_admin()` | Проверка статуса администратора с кэшированием | `utils/admin_utils.py` |
| `get_user_admin_status()` | Получение статуса через API | `utils/admin_utils.py` |

### Специальные клавиатуры для админ-редактирования

| Клавиатура | Описание | Файл |
|------------|----------|------|
| `get_word_actions_keyboard_from_study()` | Действия со словом с возвратом к изучению | `keyboards/admin_keyboards.py` |
| `get_word_edit_keyboard_from_study()` | Редактирование с дополнительной навигацией | `keyboards/admin_keyboards.py` |
| `get_word_delete_confirmation_keyboard_from_study()` | Подтверждение удаления с быстрым возвратом | `keyboards/admin_keyboards.py` |

### Управление словами (админ)

| Действие | Описание | Обработчик | Callback Constant | Файл |
|----------|----------|------------|-------------------|------|
| `edit_word_*` | Редактирование слова | `process_edit_word` | `CallbackData.EDIT_WORD_TEMPLATE` | `admin/admin_word_handlers.py` |
| `delete_word_*` | Удаление слова | `process_delete_word` | `CallbackData.DELETE_WORD_TEMPLATE` | `admin/admin_word_handlers.py` |
| `edit_wordfield_foreign_*` | Редактирование иностранного слова | `process_edit_wordfield_foreign` | `CallbackData.EDIT_WORDFIELD_FOREIGN_TEMPLATE` | `admin/admin_word_handlers.py` |
| `edit_wordfield_translation_*` | Редактирование перевода | `process_edit_wordfield_translation` | `CallbackData.EDIT_WORDFIELD_TRANSLATION_TEMPLATE` | `admin/admin_word_handlers.py` |
| `edit_wordfield_transcription_*` | Редактирование транскрипции | `process_edit_wordfield_transcription` | `CallbackData.EDIT_WORDFIELD_TRANSCRIPTION_TEMPLATE` | `admin/admin_word_handlers.py` |
| `edit_wordfield_number_*` | Редактирование номера слова | `process_edit_wordfield_number` | `CallbackData.EDIT_WORDFIELD_NUMBER_TEMPLATE` | `admin/admin_word_handlers.py` |
| `confirm_word_delete_*` | Подтверждение удаления слова | `process_confirm_word_delete` | `CallbackData.CONFIRM_WORD_DELETE_TEMPLATE` | `admin/admin_word_handlers.py` |
| `cancel_word_delete_*` | Отмена удаления слова | `process_cancel_word_delete` | `CallbackData.CANCEL_WORD_DELETE_TEMPLATE` | `admin/admin_word_handlers.py` |

## Система batch-загрузки слов

**🆕 Автоматическая загрузка партий слов для оптимальной производительности.**

### Основные характеристики

- **Размер партии**: 100 слов (`BATCH_LIMIT = 100`)
- **Автоматическая подгрузка**: при достижении конца текущей партии
- **Статистика сессии**: отслеживание обработанных слов
- **Умное кэширование**: оптимизация памяти

### Ключевые функции

| Функция | Описание | Файл |
|---------|----------|------|
| `load_next_batch()` | Загрузка следующей партии слов | `study/study_words.py` |
| `_handle_batch_completion()` | Обработка завершения партии | `study/word_actions/word_navigation_actions.py` |
| `advance_to_next_word()` | Переход к следующему слову в партии | `utils/state_models.py` |
| `load_new_batch()` | Загрузка новой партии в состояние | `utils/state_models.py` |

### Модель состояния для batch-системы

```python
# В UserWordState
batch_info = {
    "current_batch_index": 0,           # Номер текущей партии
    "batch_start_number": 1,            # Начальный номер слова в партии
    "batch_requested_count": 100,       # Запрошено слов
    "batch_received_count": 95          # Получено слов
}

session_info = {
    "total_words_processed": 45,        # Всего обработано в сессии
    "words_loaded_in_session": 195      # Всего загружено в сессии
}
```

## Meta-состояния и обработка ошибок

**🆕 Система автоматически переходит в специальные состояния при системных ошибках.**

### CommonStates (Meta-состояния)

| Состояние | Описание | Обработчик | Файл |
|-----------|----------|------------|------|
| `handling_api_error` | Обработка ошибки API | `handle_api_error_state` | `common_handlers.py` |
| `connection_lost` | Потеря соединения с сервером | `handle_connection_lost_state` | `common_handlers.py` |
| `unknown_command` | Обработка неизвестной команды | `handle_unknown_command_state` | `common_handlers.py` |

### Автоматическое восстановление

Система автоматически:
- Переходит в meta-состояния при ошибках
- Пытается восстановить соединение
- Предлагает пользователю варианты восстановления
- Сохраняет важные данные сессии

### Enhanced Middleware

| Middleware | Описание | Файл |
|------------|----------|------|
| `AuthMiddleware` | Расширенная аутентификация с meta-состояниями | `middleware/auth_middleware.py` |
| `AdminOnlyMiddleware` | Контроль доступа с улучшенной обработкой ошибок | `middleware/auth_middleware.py` |
| `StateValidationMiddleware` | **🆕 Валидация и восстановление FSM состояний** | `middleware/auth_middleware.py` |

## Голосовые подсказки

**🆕 Поддержка создания подсказок через голосовые сообщения.**

### Возможности

- **Создание подсказок голосом**: запись и автоматическое распознавание
- **Редактирование через голос**: обновление существующих подсказок
- **Смешанный ввод**: текст + голос в одной подсказке
- **Поддержка FFmpeg**: конвертация аудио для распознавания

### Ключевые утилиты

| Функция | Описание | Файл |
|---------|----------|------|
| `process_hint_input()` | Обработка текстового или голосового ввода | `utils/voice_utils.py` |
| `convert_audio()` | Конвертация аудио для Whisper | `utils/ffmpeg_utils.py` |
| `get_ffmpeg_path()` | Получение пути к FFmpeg из imageio-ffmpeg | `utils/ffmpeg_utils.py` |

## Структура обработчиков

### Приоритеты обработчиков (по порядку регистрации)

1. **common_handlers** (приоритет: самый высокий)
   - Meta-состояния и системные ошибки
   - Команды `/retry`, `/status`

2. **user_handlers** (приоритет: высокий)
   - Основные пользовательские команды
   - Подключает: basic, settings, help, stats, hint

3. **admin_handlers** (приоритет: средний)
   - Административные команды
   - **🆕 Админ-редактирование из изучения**
   - Подключает: basic, language, word, upload

4. **language_handlers** (приоритет: низкий)
   - Выбор языка изучения

5. **study_handlers** (приоритет: низкий)
   - Процесс изучения слов
   - **🆕 Включает batch-загрузку, изображения и админ-кнопки**
   - Подключает: commands, words, word_actions, hint

### Модульная организация

```
handlers/
├── common_handlers.py          # Meta-состояния
├── admin_handlers.py           # Объединяет админ-роутеры
├── user_handlers.py            # Объединяет пользовательские роутеры
├── study_handlers.py           # Объединяет роутеры изучения
├── language_handlers.py        # Выбор языка
├── admin/                      # Админ-модули
│   ├── admin_basic_handlers.py
│   ├── admin_language_handlers.py
│   ├── admin_word_handlers.py  # 🆕 Управление словами
│   └── admin_upload_handlers.py
├── user/                       # Пользовательские модули
│   ├── basic_handlers.py
│   ├── settings_handlers.py    # 🆕 С индивидуальными настройками
│   ├── help_handlers.py
│   ├── stats_handlers.py
│   └── hint_handlers.py
└── study/                      # Модули изучения
    ├── study_commands.py       # 🆕 С batch-загрузкой
    ├── study_words.py          # 🆕 Отображение и навигация
    ├── study_word_actions.py   # 🆕 Роутер действий
    ├── study_hint_handlers.py  # Роутер подсказок
    ├── hint/                   # 🆕 Подмодуль подсказок
    │   ├── common.py
    │   ├── create_handlers.py  # 🆕 С голосовым вводом
    │   ├── edit_handlers.py
    │   ├── toggle_handlers.py
    │   └── unknown.py
    └── word_actions/           # 🆕 Подмодуль действий
        ├── word_display_actions.py    # 🆕 С изображениями
        ├── word_evaluation_actions.py
        ├── word_navigation_actions.py # 🆕 С batch-загрузкой
        └── word_utility_actions.py
```

## 🆕 Новые возможности v1.4.1

### 1. **Система batch-загрузки**
- Автоматическая подгрузка партий по 100 слов
- Оптимизация производительности при больших словарях
- Статистика сессии в реальном времени

### 2. **Генерация изображений слов**
- Unicode поддержка для всех языков мира
- Автоподбор размера шрифта
- Команда `/show_big` и кнопка "🔍"

### 3. **Админ-редактирование из изучения**
- Редактирование слов без выхода из режима изучения
- Специальные клавиатуры для контекста
- Сохранение состояния изучения

### 4. **Голосовые подсказки**
- Создание подсказок через голосовые сообщения
- Автоматическое распознавание речи
- Поддержка смешанного ввода

### 5. **Индивидуальные настройки подсказок**
- Настройка каждого типа подсказки отдельно
- Bulk операции (включить/отключить все)
- Сохранение настроек между сессиями

### 6. **Meta-состояния**
- Автоматическая обработка системных ошибок
- Graceful degradation при проблемах с API
- Автоматическое восстановление соединения

