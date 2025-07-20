"""
User keyboards for Language Learning Bot.
"""

from typing import Dict, List, Optional

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.utils.callback_constants import (
    CallbackData, 
    format_language_callback,
    get_hint_setting_callback,
    HINT_SETTINGS_CALLBACKS,
    WRITING_IMAGE_SETTINGS_CALLBACKS,
)
from app.utils.hint_constants import (
    HINT_SETTING_KEYS,
    get_hint_setting_name
)
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


def create_welcome_keyboard(has_error: bool = False):
    """
    Создает клавиатуру с основными командами для приветственного сообщения.
    
    Args:
        has_error: Whether there was an error loading data
        
    Returns:
        InlineKeyboardMarkup: Welcome keyboard
    """
    builder = InlineKeyboardBuilder()
    
    if has_error:
        # Limited functionality when there's an error
        builder.add(InlineKeyboardButton(
            text="📚 Помощь",
            callback_data="show_help"
        ))
        builder.add(InlineKeyboardButton(
            text="🔄 Попробовать снова",
            callback_data="retry_start"
        ))
        builder.adjust(2)
    else:
        # Full functionality keyboard
        builder.add(InlineKeyboardButton(
            text="🌐 Выбрать язык",
            callback_data="select_language"
        ))
        builder.add(InlineKeyboardButton(
            text="📚 Помощь",
            callback_data="show_help"
        ))
        builder.add(InlineKeyboardButton(
            text="💡 О подсказках",
            callback_data="show_hint_info"
        ))
        builder.add(InlineKeyboardButton(
            text="📊 Статистика",
            callback_data="show_stats"
        ))
        
        # Layout: 2x2 grid
        builder.adjust(2, 2)
    
    return builder.as_markup()

def create_settings_keyboard(
    start_word: int = 1,
    skip_marked: bool = False,
    use_check_date: bool = True,
    show_debug: bool = False,
    show_check_date: bool = True,
    show_big: bool = False,
    show_short_captions: bool = True,
    hint_settings: Optional[Dict[str, bool]] = None,
    show_writing_images: bool = False,
    receive_messages: bool = True,
    reset_session_days: int = 1,
    reset_session_hours: int = 6,
    unknown_limit_new_words: int = 10,
) -> InlineKeyboardMarkup:
    """
    Create keyboard for user settings with individual hint settings and writing images.
    UPDATED: Removed hieroglyphic language restrictions - writing images shown based on user setting only.
    
    Args:
        start_word: Starting word number
        skip_marked: Whether to skip marked words
        use_check_date: Whether to use check date
        show_debug: Whether to show debug info
        show_check_date: Whether to show check date
        show_big: Whether to show big word
        show_short_captions: Whether to show short captions
        hint_settings: Individual hint settings dictionary
        show_writing_images: Whether writing images are enabled
        current_language: Current language information (not used for restrictions anymore)
        
    Returns:
        InlineKeyboardMarkup: Settings keyboard
    """
    builder = InlineKeyboardBuilder()
    
    # Short captions setting button
    short_captions_text = "✅ Короткие подписи" if show_short_captions else "❌ Длинные подписи"
    builder.add(InlineKeyboardButton(
        text=f"{short_captions_text}",
        callback_data=CallbackData.SETTINGS_TOGGLE_SHOW_SHORT_CAPTIONS
    ))

    # Basic settings buttons
    builder.add(InlineKeyboardButton(
        text=f"🔢 Изменить начальное слово: {start_word}",
        callback_data=CallbackData.SETTINGS_START_WORD
    ))
    
    skip_text = "❌ Исключенные слова" if skip_marked else "✅ Исключенные слова"
    builder.add(InlineKeyboardButton(
        text=f"{skip_text}",
        callback_data=CallbackData.SETTINGS_TOGGLE_SKIP_MARKED
    ))
    
    date_text = "✅ Учитывать дату" if use_check_date else "❌ Не учитывать дату"
    builder.add(InlineKeyboardButton(
        text=f"{date_text}",
        callback_data=CallbackData.SETTINGS_TOGGLE_CHECK_DATE
    ))

    check_date_text = "✅ Показывать дату" if show_check_date else "❌ Скрывать дату"
    builder.add(InlineKeyboardButton(
        text=f"{check_date_text}",
        callback_data=CallbackData.SETTINGS_TOGGLE_SHOW_CHECK_DATE
    ))
    
    # Individual hint settings buttons
    if hint_settings:
        _add_individual_hint_buttons(builder, hint_settings)
    else:
        # Fallback if no hint settings provided
        builder.add(InlineKeyboardButton(
            text="💡 Настройки подсказок недоступны",
            callback_data="no_action"
        ))
    
    # Big word setting button
    big_word_text = "✅ Показывать крупное написание" if show_big else "❌ Скрывать крупное написание"
    builder.add(InlineKeyboardButton(
        text=f"{big_word_text}",
        callback_data=CallbackData.SETTINGS_TOGGLE_SHOW_BIG
    ))

    # Writing images setting button (always show if user has setting enabled)
    writing_images_text = "✅ Показывать картинки" if show_writing_images else "❌ Скрывать картинки"
    builder.add(InlineKeyboardButton(
        text=f"{writing_images_text}",
        callback_data=CallbackData.SETTINGS_TOGGLE_WRITING_IMAGES
    ))
    
    # Debug setting
    debug_text = "✅ Отладочная информация" if show_debug else "❌ Отладочная информация"
    builder.add(InlineKeyboardButton(
        text=f"{debug_text}",
        callback_data=CallbackData.SETTINGS_TOGGLE_SHOW_DEBUG
    ))
    
    # Receive messages setting
    receive_messages_text = "✅ Получать сообщения" if receive_messages else "❌ Не получать сообщения"
    builder.add(InlineKeyboardButton(
        text=f"{receive_messages_text}",
        callback_data=CallbackData.SETTINGS_TOGGLE_RECEIVE_MESSAGES
    ))
    
    # Reset session setting
    reset_session_days_text = f"🔢 Сброс сессии (дни): {reset_session_days}"
    builder.add(InlineKeyboardButton(
        text=f"{reset_session_days_text}",
        callback_data=CallbackData.SETTINGS_TOGGLE_RESET_SESSION_DAYS
    ))

    reset_session_hours_text = f"🔢 Сброс сессии (часы): {reset_session_hours}"
    builder.add(InlineKeyboardButton(
        text=f"{reset_session_hours_text}",
        callback_data=CallbackData.SETTINGS_TOGGLE_RESET_SESSION_HOURS
    ))
    
    # Unknown limit new words setting
    unknown_limit_new_words_text = f"🔢 Лимит неизвестных слов: {unknown_limit_new_words}"
    builder.add(InlineKeyboardButton(
        text=f"{unknown_limit_new_words_text}",
        callback_data=CallbackData.SETTINGS_TOGGLE_UNKNOWN_LIMIT_NEW_WORDS
    ))
    
    # Set layout: one button per row
    builder.adjust(1)
    
    return builder.as_markup()

def _add_individual_hint_buttons(
    builder: InlineKeyboardBuilder,
    hint_settings: Dict[str, bool]
) -> None:
    """
    Add individual hint setting buttons to keyboard.
    
    Args:
        builder: Keyboard builder
        hint_settings: Individual hint settings
    """
    # Add individual hint toggle buttons
    for setting_key in HINT_SETTING_KEYS:
        setting_name = get_hint_setting_name(setting_key)
        if not setting_name:
            continue
            
        is_enabled = hint_settings.get(setting_key, True)
        status_emoji = "✅" if is_enabled else "❌"
        
        # Get callback data for this setting
        callback_data = get_hint_setting_callback(setting_key)
        if not callback_data:
            logger.warning(f"No callback found for hint setting: {setting_key}")
            continue
        
        button_text = f"   {status_emoji} {setting_name}"
        builder.add(InlineKeyboardButton(
            text=button_text,
            callback_data=callback_data
        ))


def create_language_selection_keyboard(languages: List[Dict]) -> InlineKeyboardMarkup:
    """
    Create keyboard for language selection.
    
    Args:
        languages: List of available languages
        
    Returns:
        InlineKeyboardMarkup: Language selection keyboard
    """
    builder = InlineKeyboardBuilder()
    
    for language in languages:
        language_id = language.get("id")
        name_ru = language.get("name_ru", "Неизвестный")
        name_foreign = language.get("name_foreign", "")
        
        # Format button text
        if name_foreign:
            button_text = f"🌐 {name_ru} ({name_foreign})"
        else:
            button_text = f"🌐 {name_ru}"
        
        builder.add(InlineKeyboardButton(
            text=button_text,
            callback_data=format_language_callback(language_id)
        ))
    
    # Set layout: one language per row
    builder.adjust(1)
    
    return builder.as_markup()

def create_help_keyboard() -> InlineKeyboardMarkup:
    """
    Create keyboard for help command.
    
    Returns:
        InlineKeyboardMarkup: Help keyboard
    """
    builder = InlineKeyboardBuilder()
    
    builder.add(InlineKeyboardButton(
        text="🌐 Выбрать язык",
        callback_data="select_language"
    ))
    
    builder.add(InlineKeyboardButton(
        text="💡 О подсказках",
        callback_data="show_hint_info"
    ))

    builder.add(InlineKeyboardButton(
        text="📊 Статистика",
        callback_data="show_stats"
    ))
    
    builder.adjust(1)
    
    return builder.as_markup()

def create_language_selected_keyboard() -> InlineKeyboardMarkup:
    """
    Create keyboard for when language is selected.
    Shows main actions available after language selection.
    
    Returns:
        InlineKeyboardMarkup: Language selected keyboard
    """
    builder = InlineKeyboardBuilder()
    
    builder.add(InlineKeyboardButton(
        text="📚 Начать изучение",
        callback_data="show_study"
    ))
    
    builder.add(InlineKeyboardButton(
        text="⚙️ Настройки",
        callback_data="show_settings"
    ))

    builder.add(InlineKeyboardButton(
        text="🌐 Другой язык",
        callback_data="select_language"
    ))
    
    builder.add(InlineKeyboardButton(
        text="📊 Статистика",
        callback_data="show_stats"
    ))
    
    builder.adjust(2, 2)
    
    return builder.as_markup()

def create_stats_keyboard() -> InlineKeyboardMarkup:
    """
    Create keyboard for statistics display.
    
    Returns:
        InlineKeyboardMarkup: Stats keyboard
    """
    builder = InlineKeyboardBuilder()
    
    builder.add(InlineKeyboardButton(
        text="🌐 Выбрать язык",
        callback_data="select_language"
    ))
    builder.add(InlineKeyboardButton(
        text="📚 Помощь",
        callback_data="show_help"
    ))
    builder.add(InlineKeyboardButton(
        text="💡 О подсказках",
        callback_data="show_hint_info"
    ))
    
    builder.adjust(1)
    
    return builder.as_markup()


# Export main functions
__all__ = [
    'create_settings_keyboard',
    'create_language_selection_keyboard',
    'create_help_keyboard',
    'create_stats_keyboard',
]
