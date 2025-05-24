"""
Refactored keyboards for studying words in the Language Learning Bot.
Now uses centralized callback constants and improved callback generation.
"""

from typing import List

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

# Import callback constants and utilities
from app.utils.callback_constants import CallbackData, format_hint_callback

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


def create_word_keyboard(
    word: dict, 
    word_shown: bool = False, 
    show_hints: bool = True, 
    used_hints: List[str] = None
) -> InlineKeyboardMarkup:
    """
    Create an inline keyboard for word interaction during study process.
    Shows hint buttons based on settings and existing hints.
    Now uses centralized callback constants.
    
    Args:
        word: The word data
        word_shown: Whether the word has been shown to the user
        show_hints: Whether to show hint buttons
        used_hints: List of hints already used by the user
        
    Returns:
        InlineKeyboardMarkup: The keyboard markup
    """
    # Use InlineKeyboardBuilder
    builder = InlineKeyboardBuilder()
    
    if used_hints is None:
        used_hints = []
    
    # Main action buttons based on word state
    if word_shown or (len(used_hints) > 0):
        # Word has been shown or hints used - show next word button
        builder.add(InlineKeyboardButton(
            text="➡️ Следующее слово",
            callback_data=CallbackData.NEXT_WORD
        ))
        button_layout = [1]  # 1 button in first row
    else:
        # Word not shown yet - show evaluation buttons
        builder.add(InlineKeyboardButton(
            text="✅ Я знаю это слово, к следующему",
            callback_data=CallbackData.WORD_KNOW
        ))

        builder.add(InlineKeyboardButton(
            text="❓ Не знаю / не помню / не уверен, показать",
            callback_data=CallbackData.SHOW_WORD
        ))
        button_layout = [2]  # 2 buttons in first row

    # Get word ID for hint callbacks
    word_id = _extract_word_id(word)
    
    # Add hint buttons if enabled and word_id found
    hint_buttons_added = 0
    if word_id and show_hints:
        hint_buttons_added = _add_hint_buttons(builder, word, word_id, used_hints)
        if hint_buttons_added > 0:
            button_layout.append(hint_buttons_added)

    # Add word skip toggle button
    user_word_data = word.get("user_word_data", {})
    is_skipped = user_word_data.get("is_skipped", False)
    
    builder.add(InlineKeyboardButton(
        text=f"⏩ Флаг: сменить на \"{'Не пропускать' if is_skipped else 'Пропускать'}\"",
        callback_data=CallbackData.TOGGLE_WORD_SKIP
    ))
    button_layout.append(1)  # 1 button in last row
    
    # Set dynamic layout
    builder.adjust(*button_layout)

    return builder.as_markup()


def _extract_word_id(word: dict) -> str:
    """
    Extract word ID from word data, handling different field names.
    
    Args:
        word: Word data dictionary
        
    Returns:
        str: Word ID or None if not found
    """
    word_id = None
    for id_field in ["_id", "id", "word_id"]:
        if id_field in word and word[id_field]:
            word_id = str(word[id_field])
            break
    
    if word_id:
        logger.info(f"Using word_id={word_id} for hint callbacks")
    else:
        logger.warning("No valid word_id found in word data")
    
    return word_id


def _add_hint_buttons(
    builder: InlineKeyboardBuilder, 
    word: dict, 
    word_id: str, 
    used_hints: List[str]
) -> int:
    """
    Add hint buttons to the keyboard builder.
    
    Args:
        builder: Keyboard builder to add buttons to
        word: Word data
        word_id: Word ID for callbacks
        used_hints: List of already used hints
        
    Returns:
        int: Number of hint buttons added
    """
    buttons_added = 0
    
    # Add buttons for all hint types
    for hint_type in get_all_hint_types():
        # Check if hint exists
        hint_exists = has_hint(word, hint_type)
        
        # Check if hint is currently active
        is_active = hint_type in used_hints
        
        # Format button text based on state
        button_text = format_hint_button(hint_type, hint_exists, is_active)
        
        # Determine callback action based on hint state
        if hint_exists:
            if is_active:
                # Hint is shown - allow editing
                callback_data = format_hint_callback("edit", hint_type, word_id)
                logger.info(f"Creating edit hint button with callback_data: {callback_data}")
            else:
                # Hint exists but not shown - allow toggling
                callback_data = format_hint_callback("toggle", hint_type, word_id)
                logger.info(f"Creating toggle hint button with callback_data: {callback_data}")
        else:
            # No hint exists - allow creation
            callback_data = format_hint_callback("create", hint_type, word_id)
            logger.info(f"Creating create hint button with callback_data: {callback_data}")
        
        builder.add(InlineKeyboardButton(
            text=button_text,
            callback_data=callback_data
        ))
        buttons_added += 1
    
    return buttons_added


def create_hint_actions_keyboard(word_id: str, hint_type: str) -> InlineKeyboardMarkup:
    """
    Create keyboard for hint actions (view, edit, toggle).
    
    Args:
        word_id: Word ID
        hint_type: Type of hint
        
    Returns:
        InlineKeyboardMarkup: Keyboard with hint action buttons
    """
    builder = InlineKeyboardBuilder()
    
    # View hint button
    builder.add(InlineKeyboardButton(
        text="👁️ Посмотреть подсказку",
        callback_data=format_hint_callback("view", hint_type, word_id)
    ))
    
    # Edit hint button
    builder.add(InlineKeyboardButton(
        text="✏️ Редактировать подсказку",
        callback_data=format_hint_callback("edit", hint_type, word_id)
    ))
    
    # Toggle hint visibility
    builder.add(InlineKeyboardButton(
        text="🔄 Переключить видимость",
        callback_data=format_hint_callback("toggle", hint_type, word_id)
    ))
    
    # Back to word button
    builder.add(InlineKeyboardButton(
        text="⬅️ Назад к слову",
        callback_data=CallbackData.BACK_TO_WORD
    ))
    
    builder.adjust(1)  # One button per row
    return builder.as_markup()


def create_cancel_action_keyboard() -> InlineKeyboardMarkup:
    """
    Create keyboard with cancel action button.
    
    Returns:
        InlineKeyboardMarkup: Keyboard with cancel button
    """
    builder = InlineKeyboardBuilder()
    
    builder.add(InlineKeyboardButton(
        text="❌ Отменить действие",
        callback_data=CallbackData.CANCEL_ACTION
    ))
    
    return builder.as_markup()


def create_word_navigation_keyboard(
    has_previous: bool = False, 
    has_next: bool = True,
    show_skip_button: bool = True
) -> InlineKeyboardMarkup:
    """
    Create navigation keyboard for word study process.
    
    Args:
        has_previous: Whether previous word is available
        has_next: Whether next word is available
        show_skip_button: Whether to show skip button
        
    Returns:
        InlineKeyboardMarkup: Navigation keyboard
    """
    builder = InlineKeyboardBuilder()
    
    # Navigation buttons
    nav_buttons = []
    
    if has_previous:
        nav_buttons.append(InlineKeyboardButton(
            text="⬅️ Предыдущее",
            callback_data=CallbackData.PREVIOUS_WORD
        ))
    
    if has_next:
        nav_buttons.append(InlineKeyboardButton(
            text="➡️ Следующее",
            callback_data=CallbackData.NEXT_WORD  
        ))
    
    if nav_buttons:
        builder.row(*nav_buttons)
    
    # Skip button
    if show_skip_button:
        builder.add(InlineKeyboardButton(
            text="⏭️ Пропустить слово",
            callback_data=CallbackData.TOGGLE_WORD_SKIP
        ))
    
    return builder.as_markup()


def create_word_evaluation_keyboard() -> InlineKeyboardMarkup:
    """
    Create keyboard for word evaluation (know/don't know).
    
    Returns:
        InlineKeyboardMarkup: Evaluation keyboard
    """
    builder = InlineKeyboardBuilder()
    
    builder.add(InlineKeyboardButton(
        text="✅ Знаю это слово",
        callback_data=CallbackData.WORD_KNOW
    ))
    
    builder.add(InlineKeyboardButton(
        text="❌ Не знаю это слово", 
        callback_data=CallbackData.WORD_DONT_KNOW
    ))
    
    builder.add(InlineKeyboardButton(
        text="👁️ Показать слово",
        callback_data=CallbackData.SHOW_WORD
    ))
    
    builder.adjust(2, 1)  # 2 buttons in first row, 1 in second
    return builder.as_markup()


def create_word_confirmation_keyboard() -> InlineKeyboardMarkup:
    """
    Create confirmation keyboard after word evaluation.
    
    Returns:
        InlineKeyboardMarkup: Confirmation keyboard
    """
    builder = InlineKeyboardBuilder()
    
    builder.add(InlineKeyboardButton(
        text="✅ К следующему слову",
        callback_data=CallbackData.CONFIRM_NEXT_WORD
    ))
    
    builder.add(InlineKeyboardButton(
        text="❌ Ой, все-таки не знаю",
        callback_data=CallbackData.SHOW_WORD
    ))
    
    builder.adjust(1)  # One button per row
    return builder.as_markup()
