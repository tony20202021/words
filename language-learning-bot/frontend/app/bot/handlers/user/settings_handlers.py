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
from app.utils.user_utils import get_or_create_user, validate_language_selected

# Создаем роутер для обработчиков настроек
settings_router = Router()

logger = setup_logger(__name__)

@settings_router.message(Command("settings"))
async def cmd_settings(message: Message, state: FSMContext):
    await process_settings(message, state)

@settings_router.callback_query(F.data == "show_settings")
async def process_settings_callback(callback: CallbackQuery, state: FSMContext):
    logger.info(f"'show_settings' callback from {callback.from_user.full_name}")
    
    await callback.answer("💡 Настройки")
    
    await process_settings(callback, state)

async def process_settings(message_or_callback: Message, state: FSMContext):
    """
    Handle the /settings command which shows and allows changing learning settings.
    
    Args:
        message: The message object from Telegram
        state: The FSM state context
    """
    user_id = message_or_callback.from_user.id
    username = message_or_callback.from_user.username
    full_name = message_or_callback.from_user.full_name

    logger.info(f"'/settings' command from {full_name} ({username})")

    if isinstance(message_or_callback, CallbackQuery):
        message = message_or_callback.message
    else:
        message = message_or_callback

    # Get API client
    api_client = get_api_client_from_bot(message_or_callback.bot)
    if not api_client:
        await message.answer("❌ Ошибка подключения к серверу. Попробуйте позже.")
        return

    # Ensure user exists
    db_user_id, user_data = await get_or_create_user(message_or_callback.from_user, api_client)
    if not db_user_id:
        return

    # Update state with user ID
    await state.update_data(db_user_id=db_user_id)

    # Validate language selection
    current_language = await validate_language_selected(state, message_or_callback)
    if not current_language:
        return
    
    # Set state for settings viewing
    await state.set_state(SettingsStates.viewing_settings)
    
    suffix = (
        "\n\n💡 Нажмите на кнопки ниже, чтобы изменить нужную настройку.\n\n"
        "Другие доступные команды:\n"
        "/study - начать изучение слов\n"
        "/language - выбрать другой язык для изучения\n"
    )
    
    # Display current settings with individual hint settings
    await display_language_settings(
        message_or_callback=message_or_callback,
        state=state,
        prefix="",
        suffix=suffix,
        is_callback=False
    )

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
    current_language = await validate_language_selected(state, callback)
    if not current_language:
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
    current_language = await validate_language_selected(state, callback)
    if not current_language:
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
    current_language = await validate_language_selected(state, callback)
    if not current_language:
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
    Общая функция для включения/отключения всех подсказок.
    
    Args:
        callback: The callback query
        state: FSM context
        enable_all: True to enable all hints, False to disable all
    """
    action_text = "включить" if enable_all else "отключить"
    logger.info(f"{action_text.capitalize()} all hints from {callback.from_user.full_name}")
    
    # Validate language selection
    current_language = await validate_language_selected(state, callback)
    if not current_language:
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

# Export router
__all__ = ['settings_router']
