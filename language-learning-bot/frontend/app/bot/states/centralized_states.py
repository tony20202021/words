"""
Centralized state definitions for the Language Learning Bot.
All FSM states are defined here to avoid duplication.
"""

from aiogram.fsm.state import State, StatesGroup


class UserStates(StatesGroup):
    """States for regular user operations."""
    selecting_language = State()
    viewing_stats = State()


class SettingsStates(StatesGroup):
    """States for user settings management."""
    waiting_start_word = State()  # Ожидание ввода начального слова


class StudyStates(StatesGroup):
    """States for the word learning process."""
    studying = State()  # Объединенный процесс изучения слов


class HintStates(StatesGroup):
    """States for hint management."""
    creating = State()  # Состояние создания подсказки
    editing = State()   # Состояние редактирования подсказки


class AdminStates(StatesGroup):
    """States for admin operations."""
    waiting_file = State()                      # Ожидание загрузки файла
    configuring_columns = State()               # Настройка колонок файла
    creating_language_name = State()            # Создание языка (ввод русского названия)
    creating_language_native_name = State()     # Создание языка (ввод оригинального названия)
    editing_language_name = State()             # Редактирование русского названия языка
    editing_language_native_name = State()      # Редактирование оригинального названия языка
    input_word_number = State()                 # Ввод номера слова для поиска
    input_column_number = State()               # Ввод номера колонки при загрузке файла
    managing_users = State()                    # Управление пользователями
    viewing_user_details = State()              # Просмотр деталей пользователя
    