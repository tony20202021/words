"""
State definitions for study process in the Language Learning Bot.
"""

from aiogram.fsm.state import State, StatesGroup


class StudyStates(StatesGroup):
    """States for the word learning process."""
    studying = State()  # Объединенный процесс изучения слов


class HintStates(StatesGroup):
    """States for hint management."""
    creating = State()  # Состояние создания подсказки
    editing = State()   # Состояние редактирования подсказки