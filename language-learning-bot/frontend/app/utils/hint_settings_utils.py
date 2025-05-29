"""
Centralized utilities for individual hint settings management.
This module eliminates code duplication and provides consistent hint settings handling.
"""

from typing import Dict, List, Optional, Tuple, Any, Union
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from app.utils.logger import setup_logger
from app.utils.api_utils import get_api_client_from_bot
from app.utils.error_utils import handle_api_error
from app.utils.hint_constants import (
    HINT_SETTING_KEYS, 
    get_hint_setting_name, 
    get_enabled_hint_types,
    is_hint_enabled
)
from app.utils.callback_constants import (
    get_hint_setting_from_callback,
    is_hint_setting_callback,
    HINT_SETTINGS_CALLBACKS,
    HINT_SETTINGS_CALLBACKS_REVERSE
)

logger = setup_logger(__name__)

# Default settings for individual hints
DEFAULT_HINT_SETTINGS = {
    "show_hint_meaning": True,              # Ассоциации на русском
    "show_hint_phoneticassociation": True,  # Фонетические ассоциации  
    "show_hint_phoneticsound": True,        # Звучание по слогам
    "show_hint_writing": True,              # Подсказки написания
}

async def get_individual_hint_settings(
    message_or_callback: Union[Message, CallbackQuery], 
    state: FSMContext
) -> Dict[str, bool]:
    """
    Get individual hint settings for user.
    
    Args:
        message_or_callback: Message or CallbackQuery object
        state: FSM context
        
    Returns:
        Dict with individual hint settings
    """
    # Import here to avoid circular imports
    from app.utils.settings_utils import get_user_language_settings
    
    # Get all user settings
    all_settings = await get_user_language_settings(message_or_callback, state)
    
    # Extract only hint settings
    hint_settings = {}
    for hint_key in HINT_SETTING_KEYS:
        hint_settings[hint_key] = all_settings.get(hint_key, DEFAULT_HINT_SETTINGS.get(hint_key, True))
    
    return hint_settings
        
async def save_individual_hint_settings(
    message_or_callback: Union[Message, CallbackQuery],
    state: FSMContext,
    hint_settings: Dict[str, bool]
) -> bool:
    """
    Save individual hint settings for user.
    
    Args:
        message_or_callback: Message or CallbackQuery object
        state: FSM context
        hint_settings: Dictionary with hint settings to save
        
    Returns:
        bool: True if successful
    """
    try:
        # Import here to avoid circular imports
        from app.utils.settings_utils import save_user_language_settings, get_user_language_settings
        
        # Get current settings
        current_settings = await get_user_language_settings(message_or_callback, state)
        
        logger.info(f"current_settings: {current_settings}")
        logger.info(f"hint_settings: {hint_settings}")

        # Update with new hint settings
        current_settings.update(hint_settings)
        logger.info(f"new current_settings: {current_settings}")
        
        # Save updated settings
        success = await save_user_language_settings(message_or_callback, state, current_settings)
        
        if success:
            # Update FSM state for compatibility
            await state.update_data(**hint_settings)
            logger.info(f"Saved individual hint settings: {hint_settings}")
        
        return success
        
    except Exception as e:
        logger.error(f"Error saving individual hint settings: {e}")
        return False

async def toggle_individual_hint_setting(
    message_or_callback: Union[Message, CallbackQuery],
    state: FSMContext,
    setting_key: str
) -> Tuple[bool, bool]:
    """
    Toggle individual hint setting.
    
    Args:
        message_or_callback: Message or CallbackQuery object
        state: FSM context
        setting_key: Hint setting key to toggle
        
    Returns:
        Tuple[bool, bool]: (success, new_value)
    """
    try:
        # Get current settings
        current_settings = await get_individual_hint_settings(message_or_callback, state)
        
        # Toggle the specific setting
        current_value = current_settings.get(setting_key, True)
        new_value = not current_value
        current_settings[setting_key] = new_value
        
        # Save updated settings
        success = await save_individual_hint_settings(message_or_callback, state, current_settings)
        
        if success:
            setting_name = get_hint_setting_name(setting_key)
            action = "включена" if new_value else "отключена"
            logger.info(f"Toggled hint setting {setting_name}: {action}")
        
        return success, new_value
        
    except Exception as e:
        logger.error(f"Error toggling hint setting {setting_key}: {e}")
        return False, True

async def bulk_update_hint_settings(
    message_or_callback: Union[Message, CallbackQuery],
    state: FSMContext,
    enable_all: bool
) -> bool:
    """
    Enable or disable all hint settings at once.
    
    Args:
        message_or_callback: Message or CallbackQuery object
        state: FSM context
        enable_all: True to enable all, False to disable all
        
    Returns:
        bool: True if successful
    """
    try:
        # Create settings dict with all hints set to enable_all
        hint_settings = {key: enable_all for key in HINT_SETTING_KEYS}
        
        # Save settings
        success = await save_individual_hint_settings(message_or_callback, state, hint_settings)
        
        if success:
            action = "включены" if enable_all else "отключены"
            logger.info(f"Bulk updated hint settings: все подсказки {action}")
        
        return success
        
    except Exception as e:
        logger.error(f"Error bulk updating hint settings: {e}")
        return False

def validate_hint_settings(hint_settings: Dict[str, Any]) -> Dict[str, bool]:
    """
    Validate and normalize hint settings.
    
    Args:
        hint_settings: Raw hint settings dictionary
        
    Returns:
        Dict with validated boolean settings
    """
    validated = {}
    
    for key in HINT_SETTING_KEYS:
        raw_value = hint_settings.get(key, True)
        
        # Normalize to boolean
        if isinstance(raw_value, bool):
            validated[key] = raw_value
        elif isinstance(raw_value, str):
            validated[key] = raw_value.lower() in ('true', '1', 'yes', 'on')
        elif isinstance(raw_value, (int, float)):
            validated[key] = bool(raw_value)
        else:
            validated[key] = True
            logger.warning(f"Invalid hint setting value for {key}: {raw_value}, defaulting to True")
    
    return validated

def get_hint_settings_summary(hint_settings: Dict[str, bool]) -> Dict[str, Any]:
    """
    Get summary information about hint settings.
    
    Args:
        hint_settings: Individual hint settings
        
    Returns:
        Dict with summary info
    """
    enabled_count = sum(1 for enabled in hint_settings.values() if enabled)
    total_count = len(hint_settings)
    
    enabled_types = [
        get_hint_setting_name(key) or key for key, enabled in hint_settings.items() 
        if enabled and get_hint_setting_name(key)
    ]
    
    return {
        "enabled_count": enabled_count,
        "total_count": total_count,
        "all_enabled": enabled_count == total_count,
        "all_disabled": enabled_count == 0,
        "enabled_types": enabled_types,
        "status_text": f"{enabled_count}/{total_count}",
        "percentage": (enabled_count / total_count * 100) if total_count > 0 else 0
    }

async def is_hint_type_enabled_for_user(
    hint_type: str,
    message_or_callback: Union[Message, CallbackQuery],
    state: FSMContext
) -> bool:
    """
    Check if specific hint type is enabled for user.
    
    Args:
        hint_type: Hint type to check (e.g., 'meaning', 'phoneticassociation')
        message_or_callback: Message or CallbackQuery object
        state: FSM context
        
    Returns:
        bool: True if hint type is enabled
    """
    try:
        hint_settings = await get_individual_hint_settings(message_or_callback, state)
        return is_hint_enabled(hint_type, hint_settings)
        
    except Exception as e:
        logger.error(f"Error checking if hint type {hint_type} is enabled: {e}")
        return True  # Default to enabled on error

def parse_hint_setting_callback(callback_data: str) -> Optional[str]:
    """
    Parse hint setting callback data to get setting key.
    
    Args:
        callback_data: Callback data string
        
    Returns:
        Optional[str]: Setting key or None if not a hint setting callback
    """
    if not is_hint_setting_callback(callback_data):
        return None
    
    return get_hint_setting_from_callback(callback_data)

def create_hint_settings_display_text(hint_settings: Dict[str, bool]) -> str:
    """
    Create formatted text for displaying hint settings.
    
    Args:
        hint_settings: Individual hint settings
        
    Returns:
        str: Formatted display text
    """
    summary = get_hint_settings_summary(hint_settings)
    
    text = f"💡 <b>Настройки подсказок ({summary['status_text']}):</b>\n"
    
    for key in HINT_SETTING_KEYS:
        name = get_hint_setting_name(key)
        enabled = hint_settings.get(key, True)
        status = "✅" if enabled else "❌"
        
        if name:
            text += f"   {status} {name}\n"
    
    return text

# Export main functions
__all__ = [
    'get_individual_hint_settings',
    'save_individual_hint_settings', 
    'toggle_individual_hint_setting',
    'bulk_update_hint_settings',
    'validate_hint_settings',
    'get_hint_settings_summary',
    'is_hint_type_enabled_for_user',
    'parse_hint_setting_callback',
    'create_hint_settings_display_text',
    'migrate_legacy_hint_settings',
    'DEFAULT_HINT_SETTINGS'
]
