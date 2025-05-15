"""
State definitions for administrative handlers.
"""

from aiogram.fsm.state import State, StatesGroup

# Определение состояний для FSM администратора
class AdminStates(StatesGroup):
    waiting_file = State()
    configuring_columns = State()
    creating_language_name = State()
    creating_language_native_name = State()
    editing_language_name = State()
    editing_language_native_name = State()
    # Состояние для ввода номера слова
    input_word_number = State()
    # Состояние для ввода номера колонки при загрузке файла
    input_column_number = State()