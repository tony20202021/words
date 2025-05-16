"""
Utility functions for working with user language settings.
"""

from typing import Dict, Any, Optional, Union
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from app.utils.api_utils import get_api_client_from_bot
from app.utils.logger import setup_logger
from app.utils.error_utils import handle_api_error
from app.utils.formatting_utils import format_settings_text

logger = setup_logger(__name__)

# Значения настроек по умолчанию
DEFAULT_SETTINGS = {
    "start_word": 1,
    "skip_marked": True,
    "use_check_date": True,
    "show_hints": False,
    "show_debug": False,
}

async def get_user_language_settings(message_or_callback, state: FSMContext) -> Dict[str, Any]:
    """
    Получение настроек пользователя для конкретного языка.
    Если настройки не найдены, возвращаются значения по умолчанию.
    
    Args:
        message_or_callback: Объект сообщения или callback от Telegram
        state: Контекст состояния FSM
        
    Returns:
        Dict с настройками пользователя для текущего языка
    """
    # Получаем объект бота и данные состояния
    bot = message_or_callback.bot if isinstance(message_or_callback, Message) else message_or_callback.bot
    state_data = await state.get_data()
    
    # Проверяем наличие необходимых данных
    db_user_id = state_data.get("db_user_id")
    current_language = state_data.get("current_language", {})
    language_id = current_language.get("id") if current_language else None
    
    if not db_user_id or not language_id:
        logger.warning(f"Missing user_id or language_id in state: user_id={db_user_id}, language_id={language_id}")
        return DEFAULT_SETTINGS.copy()
    
    # Получаем API клиент
    api_client = get_api_client_from_bot(bot)
    
    try:
        # Запрашиваем настройки из API
        settings_response = await api_client.get_user_language_settings(db_user_id, language_id)
        
        if settings_response["success"] and settings_response["result"]:
            # Получаем настройки из ответа API
            settings = settings_response["result"]
            
            # Обеспечиваем наличие всех необходимых полей
            for key, default_value in DEFAULT_SETTINGS.items():
                if key not in settings:
                    settings[key] = default_value
            
            logger.info(f"Retrieved settings for user {db_user_id}, language {language_id}: {settings}")
            return settings
        else:
            # Если настройки не найдены, возвращаем значения по умолчанию
            logger.info(f"Settings not found for user {db_user_id}, language {language_id}, using defaults")
            return DEFAULT_SETTINGS.copy()
    
    except Exception as e:
        logger.error(f"Error getting user language settings: {e}", exc_info=True)
        return DEFAULT_SETTINGS.copy()

async def save_user_language_settings(message_or_callback, state: FSMContext, settings: Dict[str, Any]) -> bool:
    """
    Сохранение настроек пользователя для конкретного языка.
    
    Args:
        message_or_callback: Объект сообщения или callback от Telegram
        state: Контекст состояния FSM
        settings: Словарь с настройками для сохранения
        
    Returns:
        bool: True если настройки успешно сохранены, False в противном случае
    """
    # Получаем объект бота и данные состояния
    bot = message_or_callback.bot if isinstance(message_or_callback, Message) else message_or_callback.bot
    state_data = await state.get_data()
    
    # Проверяем наличие необходимых данных
    db_user_id = state_data.get("db_user_id")
    current_language = state_data.get("current_language", {})
    language_id = current_language.get("id") if current_language else None
    
    if not db_user_id or not language_id:
        logger.warning(f"Missing user_id or language_id in state: user_id={db_user_id}, language_id={language_id}")
        return False
    
    # Получаем API клиент
    api_client = get_api_client_from_bot(bot)
    
    try:
        # Сохраняем настройки через API
        settings_response = await api_client.update_user_language_settings(db_user_id, language_id, settings)
        
        if settings_response["success"]:
            # Обновляем настройки в состоянии FSM
            await state.update_data(**settings)
            logger.info(f"Saved settings for user {db_user_id}, language {language_id}: {settings}")
            return True
        else:
            # В случае ошибки логируем её и возвращаем False
            error_msg = settings_response.get("error", "Unknown error")
            logger.error(f"Failed to save settings: {error_msg}")
            
            # Выводим ошибку пользователю, если это сообщение
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

async def display_language_settings(message_or_callback, state: FSMContext, prefix: str = "", suffix: str = "", is_callback: bool = False):
    """
    Отображение настроек языка пользователя.
    
    Args:
        message_or_callback: Объект сообщения или callback от Telegram
        state: Контекст состояния FSM
        prefix: Префикс для сообщения с настройками
        suffix: Суффикс для сообщения с настройками
        is_callback: Флаг, указывающий, что это callback
    """
    # Получаем настройки пользователя для текущего языка
    settings = await get_user_language_settings(message_or_callback, state)
    
    # Извлекаем значения настроек
    start_word = settings.get("start_word", DEFAULT_SETTINGS["start_word"])
    skip_marked = settings.get("skip_marked", DEFAULT_SETTINGS["skip_marked"])
    use_check_date = settings.get("use_check_date", DEFAULT_SETTINGS["use_check_date"])
    show_hints = settings.get("show_hints", DEFAULT_SETTINGS["show_hints"])
    show_debug = settings.get("show_debug", DEFAULT_SETTINGS["show_debug"])  # Получаем новую настройку
    
    # Получаем информацию о текущем языке из состояния
    state_data = await state.get_data()
    current_language = state_data.get("current_language", {})
    language_name = current_language.get("name_ru", "Не выбран")
    language_name_foreign = current_language.get("name_foreign", "")
    
    # Формируем заголовок с информацией о языке
    language_info = f"🌐 Язык: {language_name}"
    if language_name_foreign:
        language_info += f" ({language_name_foreign})"
    
    # Добавляем информацию о языке перед настройками
    language_prefix = prefix + language_info + "\n\n⚙️ Настройки процесса обучения:\n\n"
    
    # Импортируем функцию для создания клавиатуры настроек
    from app.bot.keyboards.user_keyboards import create_settings_keyboard
    
    # Создаем клавиатуру настроек с учетом новой настройки
    keyboard = create_settings_keyboard(skip_marked, use_check_date, show_hints, show_debug)
    
    # Если не указан суффикс, добавляем информацию о других доступных командах
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
    
    # Формируем текст настроек с учетом новой настройки
    settings_text = format_settings_text(
        start_word, skip_marked, use_check_date, show_hints, show_debug,
        prefix=language_prefix, suffix=suffix
    )
    
    # Отправляем сообщение с настройками
    if isinstance(message_or_callback, CallbackQuery):
        # Для callback обновляем существующее сообщение
        await message_or_callback.message.edit_text(
            settings_text,
            reply_markup=keyboard,
            parse_mode="HTML"
        )
    else:
        # Для нового сообщения отправляем новое
        await message_or_callback.answer(
            settings_text,
            reply_markup=keyboard,
            parse_mode="HTML"
        )
        
async def get_show_hints_setting(state_or_message, state=None):
    """
    Get show_hints setting from user's state or settings.
    
    Args:
        state_or_message: The state object or message/callback object
        state: Optional state object if state_or_message is a message/callback
        
    Returns:
        bool: True if hints should be shown, False otherwise
    """
    if state is None:
        # state_or_message is the state itself
        state_data = await state_or_message.get_data()
    else:
        # state_or_message is a message/callback and state is provided separately
        state_data = await state.get_data()
    
    # First try to get from user_language_settings
    settings = await get_user_language_settings(state_or_message, state)
    if settings is not None and "show_hints" in settings:
        return settings.get("show_hints", True)
    
    # Fallback to state data
    return state_data.get("show_hints", True)

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
    else:
        # state_or_message is a message/callback and state is provided separately
        state_data = await state.get_data()
    
    # First try to get from user_language_settings
    settings = await get_user_language_settings(state_or_message, state)
    if settings is not None and "show_debug" in settings:
        return settings.get("show_debug", False)
    
    # Fallback to state data
    return state_data.get("show_debug", False)
