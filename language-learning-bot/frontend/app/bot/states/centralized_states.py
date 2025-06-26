"""
Centralized state definitions for the Language Learning Bot.
All FSM states are defined here to avoid duplication.
UPDATED: Added viewing_word_image state for word image display.
UPDATED: Added word editing and deletion states for admin interface.
UPDATED: Added viewing_writing_image state for writing image display (hieroglyphic languages).
UPDATED: Added export states for words export functionality.
UPDATED: Added messaging states for admin message broadcasting.
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
    viewing_word_image = State()            # Просмотр изображения слова крупно
    viewing_writing_image = State()         # НОВОЕ: Просмотр картинки написания (иероглифы)


class HintStates(StatesGroup):
    """States for hint management."""
    creating = State()                      # Состояние создания подсказки
    editing = State()                       # Состояние редактирования подсказки


class AdminStates(StatesGroup):
    """States for admin operations."""
    # Основные административные состояния
    main_menu = State()                         # Главное меню администратора
    viewing_admin_stats = State()               # Просмотр административной статистики
    viewing_users_list = State()                # Просмотр списка пользователей
    viewing_user_details = State()              # Просмотр деталей пользователя
    confirming_admin_rights_change = State()    # Подтверждение изменения прав администратора
    sending_message_to_all = State()           # Отправка сообщения всем пользователям
    confirming_message_send = State()          # Подтверждение отправки сообщения
    processing_message_send = State()          # Процесс отправки сообщения
    
    # Состояния управления языками
    viewing_languages = State()                 # Просмотр списка языков
    viewing_language_details = State()          # Просмотр деталей языка
    confirming_language_deletion = State()      # Подтверждение удаления языка
    viewing_word_search_results = State()       # Просмотр результатов поиска слова
    
    # Состояния управления словами
    viewing_word_details = State()              # Просмотр деталей слова в админке
    editing_word_foreign = State()              # Редактирование иностранного слова
    editing_word_translation = State()          # Редактирование перевода
    editing_word_transcription = State()        # Редактирование транскрипции
    editing_word_number = State()               # Редактирование номера слова
    confirming_word_deletion = State()          # Подтверждение удаления слова
    
    # Состояния загрузки файлов
    waiting_file = State()                      # Ожидание загрузки файла
    configuring_columns = State()               # Настройка колонок файла
    selecting_column_template = State()         # Выбор шаблона колонок при загрузке
    configuring_upload_settings = State()      # Настройка параметров загрузки файла
    confirming_file_upload = State()           # Подтверждение загрузки файла
    
    # Состояния экспорта слов
    selecting_export_format = State()          # Выбор формата экспорта
    selecting_export_range = State()           # Выбор диапазона экспорта
    entering_export_range = State()            # Ввод диапазона экспорта
    processing_export = State()                # Обработка экспорта
    
    # Состояния создания/редактирования языков
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


class WritingImageStates(StatesGroup):
    """
    НОВОЕ: States for writing image operations (hieroglyphic languages).
    Состояния для операций с картинками написания (иероглифические языки).
    """
    generating = State()                       # Генерация картинки написания
    viewing = State()                          # Просмотр картинки написания
    error = State()                           # Ошибка генерации/отображения
    caching = State()                         # Кэширование картинки
    