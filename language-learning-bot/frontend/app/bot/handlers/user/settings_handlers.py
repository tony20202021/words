"""
Settings handlers for Language Learning Bot.
UPDATED: Support for individual hint settings management.
FIXED: Removed code duplication, improved architecture, separated concerns.
"""

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from app.utils.api_utils import get_api_client_from_bot
from app.utils.logger import setup_logger
from app.utils.error_utils import handle_api_error, validate_state_data, safe_api_call
from app.utils.settings_utils import (
    get_user_language_settings, 
    save_user_language_settings,
    display_language_settings
)
from app.utils.hint_settings_utils import (
    toggle_individual_hint_setting,
    bulk_update_hint_settings
)
from app.utils.callback_constants import (
    CallbackData,
    is_hint_setting_callback,
    get_hint_setting_from_callback
)
from app.utils.hint_constants import get_hint_setting_name
from app.bot.states.centralized_states import SettingsStates

# Создаем роутер для обработчиков настроек
settings_router = Router()

logger = setup_logger(__name__)

# НОВОЕ: Вынесенная общая функция для получения или создания пользователя
async def _ensure_user_exists(message_or_callback, api_client) -> str:
    """
    Ensure user exists in database and return user ID.
    НОВОЕ: Вынесена общая логика создания/получения пользователя.
    
    Args:
        message_or_callback: Message or CallbackQuery object
        api_client: API client instance
        
    Returns:
        str: Database user ID or None if failed
    """
    # Extract user info regardless of message type
    if hasattr(message_or_callback, 'from_user'):
        user = message_or_callback.from_user
    else:
        user = message_or_callback.message.from_user
    
    user_id = user.id
    username = user.username
    
    # Try to get existing user
    success, users = await safe_api_call(
        lambda: api_client.get_user_by_telegram_id(user_id),
        message_or_callback,
        "получение данных пользователя"
    )
    
    if not success:
        return None
    
    # Check if user exists
    existing_user = users[0] if users and len(users) > 0 else None
    
    if existing_user:
        return existing_user.get("id")
    
    # Create new user if doesn't exist
    new_user_data = {
        "telegram_id": user_id,
        "username": username,
        "first_name": user.first_name,
        "last_name": user.last_name
    }
    
    success, created_user = await safe_api_call(
        lambda: api_client.create_user(new_user_data),
        message_or_callback,
        "создание пользователя"
    )
    
    return created_user.get("id") if success and created_user else None

async def _validate_language_selected(state: FSMContext, message_or_callback) -> bool:
    """
    Validate that user has selected a language.
    НОВОЕ: Вынесена общая логика проверки выбранного языка.
    
    Args:
        state: FSM context
        message_or_callback: Message or CallbackQuery object
        
    Returns:
        bool: True if language is selected
    """
    state_data = await state.get_data()
    current_language = state_data.get("current_language")
    
    if not current_language or not current_language.get("id"):
        error_message = (
            "⚠️ Сначала выберите язык для изучения с помощью команды /language\n\n"
            "После выбора языка вы сможете настроить параметры обучения."
        )
        
        if isinstance(message_or_callback, CallbackQuery):
            await message_or_callback.answer("Язык не выбран", show_alert=True)
            await message_or_callback.message.answer(error_message)
        else:
            await message_or_callback.answer(error_message)
        
        return False
    
    return True

@settings_router.message(Command("settings"))
async def cmd_settings(message: Message, state: FSMContext):
    """
    Handle the /settings command which shows and allows changing learning settings.
    UPDATED: Simplified using common utilities, better error handling.
    
    Args:
        message: The message object from Telegram
        state: The FSM state context
    """
    user_id = message.from_user.id
    username = message.from_user.username
    full_name = message.from_user.full_name

    logger.info(f"'/settings' command from {full_name} ({username})")

    # Get API client
    api_client = get_api_client_from_bot(message.bot)
    if not api_client:
        await message.answer("❌ Ошибка подключения к серверу. Попробуйте позже.")
        return

    # Ensure user exists
    db_user_id = await _ensure_user_exists(message, api_client)
    if not db_user_id:
        return  # Error already handled in _ensure_user_exists

    # Update state with user ID
    await state.update_data(db_user_id=db_user_id)

    # Validate language selection
    if not await _validate_language_selected(state, message):
        return
    
    # Set state for settings viewing
    await state.set_state(SettingsStates.viewing_settings)
    
    # Display current settings with individual hint settings
    await display_language_settings(
        message_or_callback=message,
        state=state,
        prefix="",
        suffix="\n\n💡 Нажмите на кнопку, чтобы изменить настройку.",
        is_callback=False
    )

# ОБНОВЛЕНО: Улучшенный обработчик индивидуальных настроек подсказок
@settings_router.callback_query(lambda c: is_hint_setting_callback(c.data))
async def process_hint_setting_toggle(callback: CallbackQuery, state: FSMContext):
    """
    Process callback to toggle individual hint setting.
    ОБНОВЛЕНО: Улучшена обработка ошибок и валидация.
    
    Args:
        callback: The callback query from Telegram
        state: The FSM state context
    """
    full_name = callback.from_user.full_name
    username = callback.from_user.username

    # Get setting key from callback data
    setting_key = get_hint_setting_from_callback(callback.data)
    if not setting_key:
        await callback.answer("❌ Неизвестная настройка подсказки")
        logger.warning(f"Unknown hint setting callback: {callback.data}")
        return
    
    setting_name = get_hint_setting_name(setting_key)
    logger.info(f"'{callback.data}' callback from {full_name} ({username}) - toggling {setting_name}")
    
    # Validate language selection
    if not await _validate_language_selected(state, callback):
        return
    
    # Toggle the setting using centralized utility
    success, new_value = await toggle_individual_hint_setting(
        message_or_callback=callback,
        state=state,
        setting_key=setting_key
    )
    
    if success:
        status_text = "включена" if new_value else "отключена"
        await callback.answer(f"✅ {setting_name}: {status_text}")
        
        # Refresh settings display
        await display_language_settings(
            message_or_callback=callback,
            state=state,
            prefix=f"✅ Настройка «{setting_name}» {status_text}!\n\n",
            suffix="\n\n💡 Нажмите на кнопку, чтобы изменить настройку.",
            is_callback=True
        )
    else:
        await callback.answer("❌ Ошибка изменения настройки")

# ОБНОВЛЕНО: Улучшенные обработчики основных настроек с общими утилитами
@settings_router.callback_query(F.data == CallbackData.SETTINGS_START_WORD)
async def process_settings_start_word(callback: CallbackQuery, state: FSMContext):
    """
    Handle start word setting change.
    ОБНОВЛЕНО: Улучшена валидация и обработка ошибок.
    """
    logger.info(f"Start word setting from {callback.from_user.full_name}")
    
    # Validate language selection
    if not await _validate_language_selected(state, callback):
        return
    
    await state.set_state(SettingsStates.waiting_start_word)
    
    await callback.message.answer(
        "🔢 <b>Изменение начального слова</b>\n\n"
        "Введите номер слова, с которого хотите начать изучение.\n\n"
        "Например: <code>1</code> - начать с первого слова\n"
        "Например: <code>100</code> - начать со 100-го слова\n\n"
        "Или отправьте /cancel для отмены.",
        parse_mode="HTML"
    )
    
    await callback.answer()

@settings_router.message(SettingsStates.waiting_start_word)
async def process_start_word_input(message: Message, state: FSMContext):
    """
    Process start word input from user.
    ОБНОВЛЕНО: Улучшена валидация входных данных.
    """
    try:
        start_word = int(message.text.strip())
        
        # Validate input range
        if start_word < 1:
            await message.answer("❌ Номер слова должен быть больше 0. Попробуйте еще раз.")
            return
        
        if start_word > 50000:  # Increased reasonable limit
            await message.answer("❌ Номер слова слишком большой. Максимум: 50000. Попробуйте еще раз.")
            return
        
        # Get and update settings
        success = await _update_setting(message, state, "start_word", start_word)
        
        if success:
            await message.answer(
                f"✅ Начальное слово изменено на: <b>{start_word}</b>\n\n"
                "Теперь изучение будет начинаться с этого слова.",
                parse_mode="HTML"
            )
            
            # Return to settings view
            await state.set_state(SettingsStates.viewing_settings)
            
            # Show updated settings
            await display_language_settings(
                message_or_callback=message,
                state=state,
                prefix="⚙️ <b>Обновленные настройки обучения</b>\n\n",
                is_callback=False
            )
        else:
            await message.answer("❌ Ошибка сохранения настройки. Попробуйте позже.")
            
    except ValueError:
        await message.answer(
            "❌ Введите корректный номер слова (число).\n\n"
            "Например: <code>1</code> или <code>100</code>",
            parse_mode="HTML"
        )

# НОВОЕ: Общая функция для обновления настроек
async def _update_setting(message_or_callback, state: FSMContext, setting_key: str, new_value) -> bool:
    """
    Update a single setting value.
    НОВОЕ: Общая функция для обновления любой настройки.
    
    Args:
        message_or_callback: Message or CallbackQuery object
        state: FSM context
        setting_key: Setting key to update
        new_value: New value for the setting
        
    Returns:
        bool: True if successful
    """
    try:
        # Get current settings
        current_settings = await get_user_language_settings(message_or_callback, state)
        current_settings[setting_key] = new_value
        
        # Save updated settings
        return await save_user_language_settings(message_or_callback, state, current_settings)
        
    except Exception as e:
        logger.error(f"Error updating setting {setting_key}: {e}")
        return False

# ОБНОВЛЕНО: Упрощенные обработчики toggle с общей функцией
@settings_router.callback_query(F.data == CallbackData.SETTINGS_TOGGLE_SKIP_MARKED)
async def process_toggle_skip_marked(callback: CallbackQuery, state: FSMContext):
    """Handle skip marked words toggle."""
    await _handle_boolean_toggle(
        callback, state, "skip_marked", 
        true_text="пропускать", false_text="показывать",
        setting_name="Помеченные слова"
    )

@settings_router.callback_query(F.data == CallbackData.SETTINGS_TOGGLE_CHECK_DATE)
async def process_toggle_check_date(callback: CallbackQuery, state: FSMContext):
    """Handle check date toggle."""
    await _handle_boolean_toggle(
        callback, state, "use_check_date", 
        true_text="учитывать", false_text="не учитывать",
        setting_name="Дата проверки"
    )

@settings_router.callback_query(F.data == CallbackData.SETTINGS_TOGGLE_SHOW_DEBUG)
async def process_toggle_show_debug(callback: CallbackQuery, state: FSMContext):
    """Handle debug info toggle."""
    await _handle_boolean_toggle(
        callback, state, "show_debug", 
        true_text="показывать", false_text="скрывать",
        setting_name="Отладочная информация"
    )

# НОВОЕ: Общая функция для обработки boolean toggle
async def _handle_boolean_toggle(
    callback: CallbackQuery, 
    state: FSMContext, 
    setting_key: str, 
    true_text: str, 
    false_text: str, 
    setting_name: str
):
    """
    Handle boolean setting toggle.
    НОВОЕ: Общая функция для всех boolean настроек.
    
    Args:
        callback: The callback query
        state: FSM context
        setting_key: Setting key to toggle
        true_text: Text to show when value is True
        false_text: Text to show when value is False
        setting_name: Human-readable setting name
    """
    logger.info(f"Toggle {setting_key} from {callback.from_user.full_name}")
    
    # Validate language selection
    if not await _validate_language_selected(state, callback):
        return
    
    # Get current settings
    try:
        current_settings = await get_user_language_settings(callback, state)
        current_value = current_settings.get(setting_key, False)
        new_value = not current_value
        
        # Update settings
        success = await _update_setting(callback, state, setting_key, new_value)
        
        if success:
            status_text = true_text if new_value else false_text
            await callback.answer(f"✅ {setting_name}: {status_text}")
            
            # Refresh display
            await display_language_settings(
                message_or_callback=callback,
                state=state,
                prefix="⚙️ <b>Настройки обучения</b>\n\n",
                is_callback=True
            )
        else:
            await callback.answer("❌ Ошибка изменения настройки")
            
    except Exception as e:
        logger.error(f"Error toggling {setting_key}: {e}")
        await callback.answer("❌ Ошибка изменения настройки")

# ОБНОВЛЕНО: Bulk operations для настроек подсказок
@settings_router.callback_query(F.data == "enable_all_hints")
async def process_enable_all_hints(callback: CallbackQuery, state: FSMContext):
    """Handle enable all hints action."""
    await _handle_bulk_hints_action(callback, state, enable_all=True)

@settings_router.callback_query(F.data == "disable_all_hints")
async def process_disable_all_hints(callback: CallbackQuery, state: FSMContext):
    """Handle disable all hints action."""
    await _handle_bulk_hints_action(callback, state, enable_all=False)

# НОВОЕ: Общая функция для bulk операций с подсказками
async def _handle_bulk_hints_action(callback: CallbackQuery, state: FSMContext, enable_all: bool):
    """
    Handle bulk hint settings action.
    НОВОЕ: Общая функция для включения/отключения всех подсказок.
    
    Args:
        callback: The callback query
        state: FSM context
        enable_all: True to enable all hints, False to disable all
    """
    action_text = "включить" if enable_all else "отключить"
    logger.info(f"{action_text.capitalize()} all hints from {callback.from_user.full_name}")
    
    # Validate language selection
    if not await _validate_language_selected(state, callback):
        return
    
    success = await bulk_update_hint_settings(callback, state, enable_all=enable_all)
    
    if success:
        result_text = "включены" if enable_all else "отключены"
        await callback.answer(f"✅ Все подсказки {result_text}")
        
        # Refresh display
        await display_language_settings(
            message_or_callback=callback,
            state=state,
            prefix="⚙️ <b>Настройки обучения</b>\n\n",
            is_callback=True
        )
    else:
        await callback.answer("❌ Ошибка изменения настроек")

# Quick start word options - ОБНОВЛЕНО с общими функциями
@settings_router.callback_query(F.data.startswith("quick_start_word_"))
async def process_quick_start_word(callback: CallbackQuery, state: FSMContext):
    """
    Handle quick start word selection.
    ОБНОВЛЕНО: Улучшена обработка ошибок.
    """
    try:
        # Extract word number from callback data
        word_num_str = callback.data.replace("quick_start_word_", "")
        start_word = int(word_num_str)
        
        logger.info(f"Quick start word {start_word} from {callback.from_user.full_name}")
        
        # Validate language selection
        if not await _validate_language_selected(state, callback):
            return
        
        # Update setting
        success = await _update_setting(callback, state, "start_word", start_word)
        
        if success:
            await callback.answer(f"✅ Начальное слово: {start_word}")
            
            # Return to settings view
            await state.set_state(SettingsStates.viewing_settings)
            
            # Show updated settings
            await display_language_settings(
                message_or_callback=callback,
                state=state,
                prefix="⚙️ <b>Обновленные настройки обучения</b>\n\n",
                is_callback=True
            )
        else:
            await callback.answer("❌ Ошибка сохранения настройки")
            
    except (ValueError, IndexError) as e:
        logger.error(f"Error processing quick start word: {e}")
        await callback.answer("❌ Ошибка обработки выбора")

# Cancel handlers - moved to cancel_handlers.py, these are just for invalid input
@settings_router.message(SettingsStates.waiting_start_word)
async def handle_invalid_start_word(message: Message, state: FSMContext):
    """
    Handle invalid input during start word setting.
    ОБНОВЛЕНО: Улучшено сообщение об ошибке.
    """
    await message.answer(
        "❌ Пожалуйста, введите корректный номер слова (число от 1 до 50000).\n\n"
        "Примеры корректного ввода:\n"
        "• <code>1</code> - первое слово\n"
        "• <code>50</code> - пятидесятое слово\n"
        "• <code>100</code> - сотое слово\n\n"
        "Или отправьте /cancel для отмены.",
        parse_mode="HTML"
    )

# Export router
__all__ = ['settings_router']
