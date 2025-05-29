"""
Updated utility functions for working with user language settings.
UPDATED: Integrated individual hint settings support.
"""

from typing import Dict, Any, Optional, Union
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from app.utils.api_utils import get_api_client_from_bot
from app.utils.logger import setup_logger
from app.utils.error_utils import handle_api_error
from app.utils.formatting_utils import format_settings_text

logger = setup_logger(__name__)

# UPDATED: Default settings now include individual hint settings
DEFAULT_SETTINGS = {
    "start_word": 1,
    "skip_marked": True,
    "use_check_date": True,
    "show_debug": False,
    # Individual hint settings (новые настройки)
    "show_hint_meaning": True,
    "show_hint_phoneticassociation": True,
    "show_hint_phoneticsound": True,
    "show_hint_writing": True,
}

async def get_user_language_settings(message_or_callback, state: FSMContext) -> Dict[str, Any]:
    """
    Get user settings for specific language including individual hint settings.
    UPDATED: Integrates individual hint settings.
    
    Args:
        message_or_callback: Message or CallbackQuery object
        state: FSM context
        
    Returns:
        Dict with user settings for current language
    """
    state_data = await state.get_data()
    
    # Check required data
    db_user_id = state_data.get("db_user_id")
    current_language = state_data.get("current_language", {})
    language_id = current_language.get("id") if current_language else None

    result = await get_user_language_settings_without_state(message_or_callback, db_user_id, language_id)
    return result

async def get_user_language_settings_without_state(message_or_callback, db_user_id, language_id) -> Dict[str, Any]:
    # Get bot and state data
    bot = message_or_callback.bot if isinstance(message_or_callback, Message) else message_or_callback.bot
    
    if not db_user_id or not language_id:
        logger.warning(f"Missing user_id or language_id in state: user_id={db_user_id}, language_id={language_id}")
        return DEFAULT_SETTINGS.copy()
    
    # Get API client
    api_client = get_api_client_from_bot(bot)
    
    # Get settings from API
    settings_response = await api_client.get_user_language_settings(db_user_id, language_id)
    
    if settings_response["success"] and settings_response["result"]:
        settings = settings_response["result"]
        
        # Ensure all required fields are present
        for key, default_value in DEFAULT_SETTINGS.items():
            if key not in settings:
                settings[key] = default_value
        
        logger.info(f"Retrieved settings for user {db_user_id}, language {language_id}: settings={settings}")
        return settings
    else:
        # Settings not found, return defaults
        logger.info(f"Settings not found for user {db_user_id}, language {language_id}, using defaults")
        return DEFAULT_SETTINGS.copy()
    

async def save_user_language_settings(message_or_callback, state: FSMContext, settings: Dict[str, Any]) -> bool:
    """
    Save user settings for specific language.
    UPDATED: Handles individual hint settings.
    
    Args:
        message_or_callback: Message or CallbackQuery object
        state: FSM context
        settings: Settings dictionary to save
        
    Returns:
        bool: True if settings were saved successfully
    """
    # Get bot and state data
    bot = message_or_callback.bot if isinstance(message_or_callback, Message) else message_or_callback.bot
    state_data = await state.get_data()
    
    # Check required data
    db_user_id = state_data.get("db_user_id")
    current_language = state_data.get("current_language", {})
    language_id = current_language.get("id") if current_language else None
    
    if not db_user_id or not language_id:
        logger.warning(f"Missing user_id or language_id in state: user_id={db_user_id}, language_id={language_id}")
        return False
    
    # Get API client
    api_client = get_api_client_from_bot(bot)
    
    try:
        # Clean settings before saving
        settings_to_save = settings.copy()
        
        # Remove deprecated show_hints setting
        settings_to_save.pop("show_hints", None)
        
        # Validate individual hint settings
        from app.utils.hint_constants import HINT_SETTING_KEYS
        
        hint_settings = {k: v for k, v in settings_to_save.items() if k in HINT_SETTING_KEYS}
        if hint_settings:
            validated_hints = _validate_hint_settings(hint_settings)
            settings_to_save.update(validated_hints)
        
        # Save settings via API
        settings_response = await api_client.update_user_language_settings(db_user_id, language_id, settings_to_save)
        
        if settings_response["success"]:
            # Update FSM state
            await state.update_data(**settings_to_save)
            logger.info(f"Saved settings for user {db_user_id}, language {language_id}")
            return True
        else:
            # Handle error
            error_msg = settings_response.get("error", "Unknown error")
            logger.error(f"Failed to save settings: {error_msg}")
            
            # Show error to user if it's a message
            if isinstance(message_or_callback, Message):
                await handle_api_error(
                    settings_response,
                    message_or_callback,
                    "Error saving settings",
                    "Ошибка при сохранении настроек"
                )
            
            return False
    
    except Exception as e:
        logger.error(f"Error saving user language settings: {e}", exc_info=True)
        return False

async def display_language_settings(
    message_or_callback, 
    state: FSMContext, 
    prefix: str = "", 
    suffix: str = "", 
    is_callback: bool = False
):
    """
    Display user's language settings with individual hint settings.
    UPDATED: Uses individual hint settings display.
    
    Args:
        message_or_callback: Message or CallbackQuery object
        state: FSM context
        prefix: Prefix for settings message
        suffix: Suffix for settings message
        is_callback: Flag indicating if this is from callback
    """
    # Get user settings
    settings = await get_user_language_settings(message_or_callback, state)
    
    # Extract basic settings
    start_word = settings.get("start_word", DEFAULT_SETTINGS["start_word"])
    skip_marked = settings.get("skip_marked", DEFAULT_SETTINGS["skip_marked"])
    use_check_date = settings.get("use_check_date", DEFAULT_SETTINGS["use_check_date"])
    show_debug = settings.get("show_debug", DEFAULT_SETTINGS["show_debug"])
    
    # Extract individual hint settings
    from app.utils.hint_constants import HINT_SETTING_KEYS
    hint_settings = {}
    for hint_key in HINT_SETTING_KEYS:
        hint_settings[hint_key] = settings.get(hint_key, DEFAULT_SETTINGS[hint_key])
    
    # Get language info
    state_data = await state.get_data()
    current_language = state_data.get("current_language", {})
    language_name = current_language.get("name_ru", "Не выбран")
    language_name_foreign = current_language.get("name_foreign", "")
    
    # Format language info
    language_info = f"🌐 Язык: {language_name}"
    if language_name_foreign:
        language_info += f" ({language_name_foreign})"
    
    # Add language info to prefix
    language_prefix = language_info + "\n\n" + prefix + "⚙️ Текущие настройки:\n"
    
    # Default suffix if not provided
    if not suffix:
        suffix = (
            "\n\nДругие доступные команды:\n"
            "/study - Начать изучение слов\n"
            "/language - Выбрать другой язык для изучения\n"
            "/stats - Показать статистику\n"
            "/hint - Информация о подсказках\n"
            "/help - Получить справку\n"
            "/start - Вернуться на главный экран"
        )
    
    # Import keyboard creation function
    from app.bot.keyboards.user_keyboards import create_settings_keyboard
    
    # Create keyboard with individual hint settings
    keyboard = create_settings_keyboard(
        skip_marked=skip_marked, 
        use_check_date=use_check_date, 
        show_debug=show_debug,
        hint_settings=hint_settings
    )
    
    # Format settings text with individual hint settings
    settings_text = format_settings_text(
        start_word=start_word, 
        skip_marked=skip_marked, 
        use_check_date=use_check_date, 
        show_debug=show_debug,
        hint_settings=hint_settings,
        prefix=language_prefix, 
        suffix=suffix
    )
    
    # Send message with settings
    if isinstance(message_or_callback, CallbackQuery):
        # For callback update existing message
        await message_or_callback.message.edit_text(
            settings_text,
            reply_markup=keyboard,
            parse_mode="HTML"
        )
    else:
        # For new message send new
        await message_or_callback.answer(
            settings_text,
            reply_markup=keyboard,
            parse_mode="HTML"
        )

# НОВОЕ: Функция для проверки включения конкретного типа подсказки
async def is_hint_type_enabled(hint_type: str, state_or_message, state=None) -> bool:
    """
    Check if specific hint type is enabled in user settings.
    
    Args:
        hint_type: The hint type to check
        state_or_message: The state object or message/callback object
        state: Optional state object if state_or_message is a message/callback
        
    Returns:
        bool: True if hint type is enabled, False otherwise
    """
    from app.utils.hint_constants import get_hint_setting_key
    
    setting_key = get_hint_setting_key(hint_type)
    if not setting_key:
        return True  # Default to enabled if setting not found
    
    # Get settings based on parameter type
    if state is None:
        # state_or_message is the state itself - not supported in this function
        return True
    else:
        # state_or_message is a message/callback and state is provided separately
        settings = await get_user_language_settings(state_or_message, state)
    
    return settings.get(setting_key, True)

async def get_show_debug_setting(state_or_message, state=None):
    """
    Get show_debug setting from user's state or settings.
    
    Args:
        state_or_message: The state object or message/callback object
        state: Optional state object if state_or_message is a message/callback
        
    Returns:
        bool: True if debug info should be shown, False otherwise
    """
    if state is None:
        # state_or_message is the state itself
        state_data = await state_or_message.get_data()
        return state_data.get("show_debug", DEFAULT_SETTINGS["show_debug"])
    else:
        # state_or_message is a message/callback and state is provided separately
        settings = await get_user_language_settings(state_or_message, state)
        return settings.get("show_debug", DEFAULT_SETTINGS["show_debug"])

# ОБНОВЛЕНО: Функции совместимости для старого API
async def get_show_hints_setting(message_or_callback, state: FSMContext) -> bool:
    """
    Get show_hints setting - DEPRECATED: kept for backward compatibility.
    Now checks if any individual hint is enabled.
    
    Args:
        message_or_callback: Message or CallbackQuery object
        state: FSM context
        
    Returns:
        bool: True if any hint type is enabled
    """
    settings = await get_user_language_settings(message_or_callback, state)
    
    # Check if any individual hint is enabled
    from app.utils.hint_constants import HINT_SETTING_KEYS
    return any(settings.get(key, True) for key in HINT_SETTING_KEYS)

async def get_hint_settings(message_or_callback, state: FSMContext) -> Dict[str, bool]:
    """
    Get individual hint settings - NEW: wrapper for hint_settings_utils.
    
    Args:
        message_or_callback: Message or CallbackQuery object
        state: FSM context
        
    Returns:
        Dict with individual hint settings
    """
    # Import here to avoid circular imports
    from app.utils.hint_settings_utils import get_individual_hint_settings
    return await get_individual_hint_settings(message_or_callback, state)

def _validate_hint_settings(hint_settings: Dict[str, Any]) -> Dict[str, bool]:
    """
    Validate and normalize hint settings.
    
    Args:
        hint_settings: Raw hint settings dictionary
        
    Returns:
        Dict with validated boolean settings
    """
    from app.utils.hint_constants import HINT_SETTING_KEYS
    
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
