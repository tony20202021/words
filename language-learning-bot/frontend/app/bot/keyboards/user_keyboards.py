"""
User keyboards for Language Learning Bot.
UPDATED: Support for individual hint settings in user interface.
FIXED: Proper separation of keyboard creation from handlers.
"""

from typing import Dict, List, Optional

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.utils.callback_constants import (
    CallbackData, 
    format_language_callback,
    get_hint_setting_callback,
    HINT_SETTINGS_CALLBACKS
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
    skip_marked: bool = False,
    use_check_date: bool = True,
    show_debug: bool = False,
    hint_settings: Optional[Dict[str, bool]] = None
) -> InlineKeyboardMarkup:
    """
    Create keyboard for user settings with individual hint settings.
    
    Args:
        skip_marked: Whether to skip marked words
        use_check_date: Whether to use check date
        show_debug: Whether to show debug info
        hint_settings: Individual hint settings dictionary
        
    Returns:
        InlineKeyboardMarkup: Settings keyboard
    """
    builder = InlineKeyboardBuilder()
    
    # Basic settings buttons
    builder.add(InlineKeyboardButton(
        text="🔢 Изменить начальное слово",
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
    
    # НОВОЕ: Individual hint settings buttons
    if hint_settings:
        _add_individual_hint_buttons(builder, hint_settings)
    else:
        # Fallback if no hint settings provided
        builder.add(InlineKeyboardButton(
            text="💡 Настройки подсказок недоступны",
            callback_data="no_action"
        ))
    
    # Debug setting
    debug_text = "✅ Отладочная информация" if show_debug else "❌ Отладочная информация"
    builder.add(InlineKeyboardButton(
        text=f"{debug_text}",
        callback_data=CallbackData.SETTINGS_TOGGLE_SHOW_DEBUG
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

def create_start_word_input_keyboard() -> InlineKeyboardMarkup:
    """
    Create keyboard for start word input with quick options.
    
    Returns:
        InlineKeyboardMarkup: Start word input keyboard
    """
    builder = InlineKeyboardBuilder()
    
    # Quick options for common start words
    quick_options = [1, 10, 50, 100, 500, 1000]
    
    for word_num in quick_options:
        builder.add(InlineKeyboardButton(
            text=f"📖 Слово #{word_num}",
            callback_data=f"quick_start_word_{word_num}"
        ))
    
    # Cancel button
    builder.add(InlineKeyboardButton(
        text="❌ Отменить",
        callback_data=CallbackData.CANCEL_ACTION
    ))
    
    # Layout: 2 options per row, cancel on separate row
    builder.adjust(2, 2, 2, 1)
    
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

# НОВОЕ: Specialized keyboards for hint settings management
def create_hint_settings_keyboard(hint_settings: Dict[str, bool]) -> InlineKeyboardMarkup:
    """
    Create specialized keyboard for hint settings management.
    
    Args:
        hint_settings: Individual hint settings
        
    Returns:
        InlineKeyboardMarkup: Hint settings keyboard
    """
    builder = InlineKeyboardBuilder()
    
    # Header with current status
    enabled_count = sum(1 for enabled in hint_settings.values() if enabled)
    total_count = len(hint_settings)
    
    builder.add(InlineKeyboardButton(
        text=f"💡 Настройки подсказок ({enabled_count}/{total_count})",
        callback_data="no_action"
    ))
    
    # Individual hint toggles
    for setting_key in HINT_SETTING_KEYS:
        setting_name = get_hint_setting_name(setting_key)
        if not setting_name:
            continue
            
        is_enabled = hint_settings.get(setting_key, True)
        status_emoji = "✅" if is_enabled else "❌"
        
        callback_data = get_hint_setting_callback(setting_key)
        if callback_data:
            builder.add(InlineKeyboardButton(
                text=f"{status_emoji} {setting_name}",
                callback_data=callback_data
            ))
    
    # Bulk actions
    if enabled_count < total_count:
        builder.add(InlineKeyboardButton(
            text="✅ Включить все подсказки",
            callback_data="enable_all_hints"
        ))
    
    if enabled_count > 0:
        builder.add(InlineKeyboardButton(
            text="❌ Отключить все подсказки", 
            callback_data="disable_all_hints"
        ))
    
    # Back button
    builder.add(InlineKeyboardButton(
        text="⬅️ Назад к настройкам",
        callback_data="back_to_settings"
    ))
    
    builder.adjust(1)
    
    return builder.as_markup()

def create_confirmation_keyboard(
    confirm_text: str = "✅ Подтвердить",
    cancel_text: str = "❌ Отменить",
    confirm_callback: str = "confirm_action",
    cancel_callback: str = "cancel_action"
) -> InlineKeyboardMarkup:
    """
    Create generic confirmation keyboard.
    
    Args:
        confirm_text: Text for confirm button
        cancel_text: Text for cancel button
        confirm_callback: Callback data for confirm
        cancel_callback: Callback data for cancel
        
    Returns:
        InlineKeyboardMarkup: Confirmation keyboard
    """
    builder = InlineKeyboardBuilder()
    
    builder.add(InlineKeyboardButton(
        text=confirm_text,
        callback_data=confirm_callback
    ))
    
    builder.add(InlineKeyboardButton(
        text=cancel_text,
        callback_data=cancel_callback
    ))
    
    builder.adjust(2)
    
    return builder.as_markup()

# НОВОЕ: Utility functions for keyboard creation
def create_back_button_keyboard(back_callback: str = "back_to_menu") -> InlineKeyboardMarkup:
    """
    Create keyboard with just a back button.
    
    Args:
        back_callback: Callback data for back button
        
    Returns:
        InlineKeyboardMarkup: Back button keyboard
    """
    builder = InlineKeyboardBuilder()
    
    builder.add(InlineKeyboardButton(
        text="⬅️ Назад",
        callback_data=back_callback
    ))
    
    return builder.as_markup()

def validate_hint_settings_for_keyboard(hint_settings: Optional[Dict[str, bool]]) -> Dict[str, bool]:
    """
    Validate hint settings before creating keyboard.
    
    Args:
        hint_settings: Raw hint settings
        
    Returns:
        Dict: Validated hint settings
    """
    if not hint_settings:
        from app.utils.hint_settings_utils import DEFAULT_HINT_SETTINGS
        return DEFAULT_HINT_SETTINGS.copy()
    
    validated = {}
    for key in HINT_SETTING_KEYS:
        validated[key] = hint_settings.get(key, True)
    
    return validated

def get_hint_settings_summary_text(hint_settings: Dict[str, bool]) -> str:
    """
    Get summary text for hint settings status.
    
    Args:
        hint_settings: Individual hint settings
        
    Returns:
        str: Summary text
    """
    enabled_count = sum(1 for enabled in hint_settings.values() if enabled)
    total_count = len(hint_settings)
    
    if enabled_count == total_count:
        return "Все включены ✅"
    elif enabled_count == 0:
        return "Все отключены ❌"
    else:
        return f"{enabled_count}/{total_count} включено 🔄"

# Export main functions
__all__ = [
    'create_settings_keyboard',
    'create_language_selection_keyboard',
    'create_start_word_input_keyboard',
    'create_help_keyboard',
    'create_stats_keyboard',
    'create_hint_settings_keyboard',
    'create_confirmation_keyboard',
    'create_back_button_keyboard',
    'validate_hint_settings_for_keyboard',
    'get_hint_settings_summary_text'
]
