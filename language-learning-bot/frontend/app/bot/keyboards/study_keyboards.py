"""
Keyboards for studying words in the Language Learning Bot.
Contains keyboard builders for the word learning process.
"""

from typing import List

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.utils.hint_constants import (
    get_all_hint_types,
    get_hint_key,
    get_hint_name,
    get_hint_icon,
    format_hint_button,
    has_hint
)
from app.utils.logger import setup_logger


logger = setup_logger(__name__)

def create_word_keyboard(word: dict, word_shown: bool = False, show_hints: bool = True, active_hints: List[str] = None, used_hints: List[str] = None) -> InlineKeyboardMarkup:
    """
    Create an inline keyboard for word interaction during study process.
    Shows hint buttons based on settings and existing hints.
    
    Args:
        word: The word data
        word_shown: Whether the word has been shown to the user
        show_hints: Whether to show hint buttons
        active_hints: List of currently active hint types
        used_hints: List of hints already used by the user
        
    Returns:
        InlineKeyboardMarkup: The keyboard markup
    """
    # Use InlineKeyboardBuilder
    builder = InlineKeyboardBuilder()
    
    # Initialize active_hints and used_hints if None
    if active_hints is None:
        active_hints = []
    if used_hints is None:
        used_hints = []
    
    # Кнопка для показа слова с учетом состояния показа
    if word_shown or (len(used_hints) > 0):
        builder.add(InlineKeyboardButton(
            text="➡️ Следующее слово",
            callback_data="next_word"
        ))
        builder_adjust = (1, 1, 1, 1, 1, 1)
    else:
        # Main action buttons
        builder.add(InlineKeyboardButton(
            text="✅ Я знаю это слово, к следующему",
            callback_data="word_know"
        ))

        builder.add(InlineKeyboardButton(
            text="❓ Не знаю  / не помню / не уверен, показать",
            callback_data="show_word"
        ))
        builder_adjust =(2, 1, 1, 1, 1, 1)

    # Get word ID from different possible fields, ensuring we use string type
    word_id = None
    for id_field in ["_id", "id", "word_id"]:
        if id_field in word and word[id_field]:
            word_id = str(word[id_field])
            break
    
    # Логирование найденного ID
    logger.info(f"Using word_id={word_id} in create_word_keyboard for callbacks")
    
    # Добавляем кнопки подсказок только если show_hints=True и word_id найден
    if word_id and show_hints:
        # Add buttons for all hint types
        for hint_type in get_all_hint_types():
                
            # Проверяем, есть ли подсказка
            hint_exists = has_hint(word, hint_type)
            
            # Проверяем, активна ли подсказка в данный момент
            is_active = hint_type in active_hints
            
            # Формируем текст кнопки в зависимости от состояния
            button_text = format_hint_button(hint_type, hint_exists, is_active)
            
            # Добавляем соответствующую кнопку
            if hint_exists:
                if is_active:
                    # Если подсказка уже показана - даем редактировать
                    callback_data = f"hint_edit_{hint_type}_{word_id}"
                    logger.info(f"Creating edit hint button with callback_data: {callback_data}")
                    builder.add(InlineKeyboardButton(
                        text=button_text,
                        callback_data=callback_data
                    ))
                else:
                    # Если подсказка не показана, кнопка будет переключать её видимость
                    callback_data = f"hint_toggle_{hint_type}_{word_id}"
                    logger.info(f"Creating toggle hint button with callback_data: {callback_data}")
                    builder.add(InlineKeyboardButton(
                        text=button_text,
                        callback_data=callback_data
                    ))
            else:
                # Если подсказки нет, кнопка будет создавать новую подсказку
                callback_data = f"hint_create_{hint_type}_{word_id}"
                logger.info(f"Creating create hint button with callback_data: {callback_data}")
                builder.add(InlineKeyboardButton(
                    text=button_text,
                    callback_data=callback_data
                ))
    
    # Проверяем наличие данных пользователя и флага пропуска
    user_word_data = word.get("user_word_data", {})
    is_skipped = user_word_data.get("is_skipped", False)

    # Кнопка для пропуска слова с текстом, зависящим от текущего статуса
    builder.add(InlineKeyboardButton(
        text=f"⏩ Флаг: сменить на \"{'Не пропускать' if is_skipped else 'Пропускать'}\"",
        callback_data="toggle_word_skip"
    ))
    
    # Задаем правильное расположение кнопок
    builder.adjust(*builder_adjust)

    return builder.as_markup()
