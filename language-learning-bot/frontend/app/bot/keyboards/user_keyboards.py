"""
Refactored keyboards for user interactions.
Now uses centralized callback constants.
"""

from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

# Import callback constants
from app.utils.callback_constants import CallbackData


def create_settings_keyboard(skip_marked: bool, use_check_date: bool, show_hints: bool, show_debug: bool):
    """
    Create keyboard for settings menu.
    Now uses centralized callback constants.
    
    Args:
        skip_marked: Whether to skip marked words
        use_check_date: Whether to use check date
        show_hints: Whether to show hint buttons
        show_debug: Whether to show debug information
        
    Returns:
        InlineKeyboardMarkup: Settings keyboard markup
    """
    # Create keyboard builder
    builder = InlineKeyboardBuilder()
    
    # Add buttons using constants
    builder.add(InlineKeyboardButton(
        text="🔢 Изменить начальное слово",
        callback_data=CallbackData.SETTINGS_START_WORD
    ))
    
    builder.add(InlineKeyboardButton(
        text=f"⏩ Помеченные слова: сменить на \"{'Показывать' if skip_marked else 'Пропускать'}\"",
        callback_data=CallbackData.SETTINGS_TOGGLE_SKIP_MARKED
    ))

    builder.add(InlineKeyboardButton(
        text=f"📅 Период проверки: сменить на \"{'Не учитывать' if use_check_date else 'Учитывать'}\"",
        callback_data=CallbackData.SETTINGS_TOGGLE_CHECK_DATE
    ))
    
    builder.add(InlineKeyboardButton(
        text=f"💡 Подсказки: сменить на \"{'Пропускать' if show_hints else 'Придумывать'}\"",
        callback_data=CallbackData.SETTINGS_TOGGLE_SHOW_HINTS
    ))
    
    # Add debug information toggle button
    builder.add(InlineKeyboardButton(
        text=f"🔍 Отладочная информация: сменить на \"{'Скрывать' if show_debug else 'Показывать'}\"",
        callback_data=CallbackData.SETTINGS_TOGGLE_SHOW_DEBUG
    ))
    
    # Set layout: 1 button per row
    builder.adjust(1)
    
    return builder.as_markup()


def get_skip_marked_button_text(skip_marked: bool) -> str:
    """
    Get text for skip marked button based on current state.
    
    Args:
        skip_marked: Current skip marked state
        
    Returns:
        str: Button text
    """
    return f"⏩ Помеченные слова: сменить на \"{'Показывать' if skip_marked else 'Пропускать'}\""


def get_check_date_button_text(use_check_date: bool) -> str:
    """
    Get text for check date button based on current state.
    
    Args:
        use_check_date: Current check date state
        
    Returns:
        str: Button text
    """
    return f"📅 Период проверки: сменить на \"{'Не учитывать' if use_check_date else 'Учитывать'}\""


def get_start_word_button_text() -> str:
    """
    Get text for start word button.
    
    Returns:
        str: Button text
    """
    return "🔢 Изменить начальное слово"


def get_show_hints_button_text(show_hints: bool) -> str:
    """
    Get text for show hints button based on current state.
    
    Args:
        show_hints: Current show hints state
        
    Returns:
        str: Button text
    """
    return f"💡 Подсказки: сменить на \"{'Пропускать' if show_hints else 'Придумывать'}\""


def get_show_debug_button_text(show_debug: bool) -> str:
    """
    Get text for show debug button based on current state.
    
    Args:
        show_debug: Current show debug state
        
    Returns:
        str: Button text
    """
    return f"🔍 Отладочная информация: сменить на \"{'Скрывать' if show_debug else 'Показывать'}\""


# Convenience functions for creating individual buttons
def create_settings_start_word_button() -> InlineKeyboardButton:
    """Create start word settings button."""
    return InlineKeyboardButton(
        text=get_start_word_button_text(),
        callback_data=CallbackData.SETTINGS_START_WORD
    )


def create_settings_skip_marked_button(skip_marked: bool) -> InlineKeyboardButton:
    """Create skip marked settings button."""
    return InlineKeyboardButton(
        text=get_skip_marked_button_text(skip_marked),
        callback_data=CallbackData.SETTINGS_TOGGLE_SKIP_MARKED
    )


def create_settings_check_date_button(use_check_date: bool) -> InlineKeyboardButton:
    """Create check date settings button."""
    return InlineKeyboardButton(
        text=get_check_date_button_text(use_check_date),
        callback_data=CallbackData.SETTINGS_TOGGLE_CHECK_DATE
    )


def create_settings_show_hints_button(show_hints: bool) -> InlineKeyboardButton:
    """Create show hints settings button."""
    return InlineKeyboardButton(
        text=get_show_hints_button_text(show_hints),
        callback_data=CallbackData.SETTINGS_TOGGLE_SHOW_HINTS
    )


def create_settings_show_debug_button(show_debug: bool) -> InlineKeyboardButton:
    """Create show debug settings button."""
    return InlineKeyboardButton(
        text=get_show_debug_button_text(show_debug),
        callback_data=CallbackData.SETTINGS_TOGGLE_SHOW_DEBUG
    )
