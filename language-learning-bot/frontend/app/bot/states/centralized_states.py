"""
Centralized state definitions for the Language Learning Bot.
All FSM states are defined here to avoid duplication.
"""

from aiogram.fsm.state import State, StatesGroup


class UserStates(StatesGroup):
    """States for regular user operations."""
    selecting_language = State()
    viewing_stats = State()
    viewing_help = State()
    viewing_hint_info = State()


class SettingsStates(StatesGroup):
    """States for user settings management."""
    viewing_settings = State()              # Основной экран настроек
    waiting_start_word = State()            # Ожидание ввода начального слова
    confirming_changes = State()            # Подтверждение изменения настроек


class StudyStates(StatesGroup):
    """States for the word learning process."""
    studying = State()                      # Основной процесс изучения слов
    confirming_word_knowledge = State()     # Подтверждение знания слова
    viewing_word_details = State()          # Просмотр деталей слова после оценки
    study_completed = State()               # Завершение изучения (все слова изучены)


class HintStates(StatesGroup):
    """States for hint management."""
    creating = State()                      # Состояние создания подсказки
    editing = State()                       # Состояние редактирования подсказки
    viewing = State()                       # Просмотр существующей подсказки
    confirming_deletion = State()           # Подтверждение удаления подсказки


class AdminStates(StatesGroup):
    """States for admin operations."""
    # Основные административные состояния
    main_menu = State()                         # Главное меню администратора ✅ НОВОЕ
    viewing_admin_stats = State()               # Просмотр административной статистики ✅ НОВОЕ
    viewing_users_list = State()                # Просмотр списка пользователей ✅ НОВОЕ
    viewing_user_details = State()              # Просмотр деталей пользователя
    confirming_admin_rights_change = State()    # Подтверждение изменения прав администратора ✅ НОВОЕ
    
    # Состояния управления языками
    viewing_languages = State()                 # Просмотр списка языков ✅ НОВОЕ
    viewing_language_details = State()          # Просмотр деталей языка ✅ НОВОЕ
    confirming_language_deletion = State()      # Подтверждение удаления языка ✅ НОВОЕ
    viewing_word_search_results = State()       # Просмотр результатов поиска слова ✅ НОВОЕ
    
    # Существующие состояния загрузки файлов
    waiting_file = State()                      # Ожидание загрузки файла
    configuring_columns = State()               # Настройка колонок файла
    selecting_column_template = State()         # Выбор шаблона колонок при загрузке ✅ НОВОЕ
    configuring_upload_settings = State()      # Настройка параметров загрузки файла ✅ НОВОЕ
    confirming_file_upload = State()           # Подтверждение загрузки файла ✅ НОВОЕ
    
    # Существующие состояния создания/редактирования языков
    creating_language_name = State()            # Создание языка (ввод русского названия)
    creating_language_native_name = State()     # Создание языка (ввод оригинального названия)
    editing_language_name = State()             # Редактирование русского названия языка
    editing_language_native_name = State()      # Редактирование оригинального названия языка
    input_word_number = State()                 # Ввод номера слова для поиска
    input_column_number = State()               # Ввод номера колонки при загрузке файла
    managing_users = State()                    # Управление пользователями


class CommonStates(StatesGroup):
    """Meta-states for common error handling and system operations."""
    handling_api_error = State()               # Обработка ошибки API
    connection_lost = State()                  # Ожидание восстановления соединения
    unknown_command = State()                  # Обработка неизвестной команды
    