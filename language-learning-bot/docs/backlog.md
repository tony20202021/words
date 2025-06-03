# 📋 Backlog проекта Language Learning Bot

## 🎯 Задачи для улучшения проекта


---
### генерировать мультяшные картинки-комиксы-иллюстрации для написания
---
### админ - сделать
и обратно - выгрузку из БД в файл
---

### 5. 🔔 **Webhook для real-time уведомлений**

**Описание:** Система для отправки уведомлений пользователям без их запроса для повышения вовлеченности.

#### **Функциональность:**

**5.1. Напоминания о повторении слов**
- Отправка уведомлений, когда у пользователя есть слова для повторения
- Кнопки быстрого доступа:
  ```
  [🚀 Начать повторение]
  [📖 Повторить Английский...]  [📖 Повторить Немецкий...]
  [⏰ Напомнить через час]
  ```

**5.2. Уведомления об окончании технических работ**
- Информирование пользователей о завершении обновлений системы
- Приглашение продолжить изучение после перезагрузки

**5.3. Система достижений**
- Уведомления о достижениях:
  - 🎉 Первое изученное слово
  - 🌟 10, 50, 100 изученных слов  
  - 📅 Неделя непрерывного изучения
  - 🎓 80% прогресса по языку

**5.4. Streak уведомления**
- Поздравления с достижением streak (дни подряд изучения)
- Напоминания о возможной потере streak

#### **Техническая реализация:**

**Backend компоненты:**
- `ReminderService` - проверка и отправка напоминаний
- `AchievementService` - отслеживание достижений
- Cron-задачи для периодической проверки
- Webhook эндпоинты для получения уведомлений

**Frontend компоненты:**
- `NotificationWebhookHandler` - обработка входящих webhook
- Обработчики для кнопок быстрого доступа
- Интеграция с основным процессом изучения

**Настройка webhook:**
- FastAPI эндпоинты: `/webhook/reminders`, `/webhook/achievements`
- Модели данных для разных типов уведомлений
- Система авторизации webhook запросов

---

---
### 2. статусы
- с любого экрана - разрешить перезапуск /start
- юнит-тесты

---

### Добавить middleware для автоматического восстановления
Enhanced Auto-Recovery Middleware for Language Learning Bot.
Automatically handles state transitions and error recovery.
Middleware for automatic error recovery and state management.
    Handles meta-states and provides seamless user experience.
---
### Система метрик и аналитики
Enhanced Metrics & Analytics System for Language Learning Bot.
Provides detailed learning analytics and performance tracking.
---

### 4. 🎬 **Создать обучающее видео для пользователей**

**Описание:** Пользователям нужна наглядная инструкция по использованию бота. Видео можно отправлять при первом запуске или по команде.

**Задачи:**
- Создать короткое видео (2-3 минуты) с демонстрацией:
  - Выбор языка для изучения
  - Настройка процесса обучения
  - Процесс изучения слов
  - Создание и использование подсказок
  - Просмотр статистики
- Добавить команду `/tutorial` или `/video`
- Встроить отправку видео в команду `/start` для новых пользователей
- Добавить кнопку "📹 Посмотреть инструкцию" в главное меню

**Технические детали:**
- Загрузить видео на Telegram через BotFather
- Получить `file_id` видео
- Добавить отправку видео в соответствующие обработчики

---





###

Проанализировав весь предоставленный код, вот что я нашел:
🔍 1. "Фантомные" функции (определены, но не используются):
admin_utils.py:

get_user_and_admin_info() - комплексная функция получения пользователя и админ-статуса, но везде используются отдельные функции
admin_required() - декоратор для проверки прав админа, но в коде используется прямая проверка через ensure_user_admin_rights()

callback_constants.py:

format_word_callback() - форматирование callback'ов для слов, но используются прямые шаблоны
format_word_field_callback() - форматирование для полей слов, не используется
get_all_hint_setting_callbacks() - получение всех callback'ов подсказок, нигде не вызывается
format_hint_setting_callback() - есть аналогичная логика в других местах

error_utils.py:

get_contextual_error_message() - большая функция получения контекстных сообщений, но используется более простая логика
validate_user_session() - комплексная валидация сессии, но используются отдельные проверки
safe_state_operation() - обертка для безопасных операций, нигде не используется
check_system_health() - проверка здоровья системы, определена но не вызывается
auto_recover_from_error_state() - автовосстановление, не используется

formatting_utils.py:

format_hint_settings_summary() - краткая сводка настроек подсказок
format_hint_settings_detailed() - детальное описание настроек
get_hint_settings_status_text() - текст статуса для кнопок
validate_hint_settings() - валидация настроек (есть дубль в других файлах)

state_models.py:

get_session_statistics() - статистика сессии, определена но не используется
get_appropriate_study_state() - определение подходящего состояния, не вызывается
transition_to_appropriate_state() - переход в подходящее состояние
is_in_completion_state() - проверка состояния завершения

study_keyboards.py:

validate_hint_settings_for_keyboard() - валидация настроек для клавиатуры
should_show_hint_buttons() - определение показа кнопок подсказок
should_show_word_image_button() - определение показа кнопки изображения
should_show_admin_edit_button() - определение показа кнопки админ-редактирования

study_words.py:

get_available_hint_actions() - получение доступных действий с подсказками
validate_word_display_state() - валидация состояния для отображения
refresh_word_display_after_settings_change() - обновление отображения после изменения настроек
get_hint_usage_stats() - статистика использования подсказок

study_commands.py:

validate_study_readiness() - валидация готовности к изучению
_validate_hint_settings_compatibility() - проверка совместимости настроек подсказок

user_keyboards.py:

create_welcome_keyboard() - клавиатура приветствия, нигде не используется
create_language_selected_keyboard() - используется только в language_handlers
create_start_word_input_keyboard() - клавиатура ввода начального слова
create_hint_settings_keyboard() - специализированная клавиатура настроек подсказок
create_confirmation_keyboard() - универсальная клавиатура подтверждения
create_back_button_keyboard() - клавиатура с кнопкой "Назад"
get_router_info() - информация о структуре роутеров для отладки

🔄 2. Функции с сильным дублированием (>50% кода):
Валидация настроек подсказок:

formatting_utils.validate_hint_settings()
hint_settings_utils.validate_hint_settings()
settings_utils._validate_hint_settings()
Дублирование: ~80% - все делают одно и то же

Получение настроек подсказок:

settings_utils.get_hint_settings()
hint_settings_utils.get_individual_hint_settings()
Дублирование: ~70% - практически идентичная логика

Отображение настроек подсказок:

formatting_utils.format_hint_settings_summary()
formatting_utils.format_hint_settings_detailed()
hint_settings_utils.create_hint_settings_display_text()
user_keyboards.get_hint_settings_summary_text()
Дублирование: ~60% - разные форматы одной информации

Проверка прав администратора:

admin_utils.is_user_admin()
admin_utils.get_user_admin_status()
Дублирование: ~65% - частично перекрывающаяся логика

Создание клавиатур с кнопками назад:

admin_keyboards.get_back_to_admin_keyboard()
admin_keyboards.get_back_to_languages_keyboard()
admin_keyboards.get_word_back_keyboard()
user_keyboards.create_back_button_keyboard()
Дублирование: ~70% - одинаковый паттерн создания

Обработка отмены в разных состояниях:

cancel_handlers._process_state_cancel()
common.cancel_hint_editing()
create_handlers.cancel_hint_creation()
Дублирование: ~60% - схожая логика возврата к изучению

Форматирование сообщений об ошибках:

error_utils.send_contextual_help()
cancel_handlers._get_main_menu_commands()
cancel_handlers._get_study_menu_commands()
Дублирование: ~55% - похожие списки команд

CallbackAsMessage классы:

В study_commands.py определены несколько практически идентичных классов-оберток для преобразования CallbackQuery в Message-подобные объекты
Дублирование: ~90% - копипаста

📊 Итого:

Фантомных функций: ~25
Групп дублирующихся функций: ~8 групп с 2-4 функциями в каждой

Основные проблемы концентрируются вокруг настроек подсказок, валидации состояний и создания клавиатур - там больше всего избыточности.