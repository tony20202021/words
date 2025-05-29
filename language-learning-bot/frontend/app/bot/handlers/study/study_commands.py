"""
Study command handlers for Language Learning Bot.
Handles the /study command and study initialization.
UPDATED: Support for individual hint settings.
"""

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from app.utils.api_utils import get_api_client_from_bot
from app.utils.logger import setup_logger
from app.utils.error_utils import handle_api_error
from app.utils.state_models import UserWordState
from app.utils.settings_utils import get_user_language_settings, get_hint_settings
from app.bot.states.centralized_states import StudyStates
from app.bot.handlers.study.study_words import show_study_word, load_next_batch

# Создаем роутер для команд изучения
study_router = Router()

logger = setup_logger(__name__)

@study_router.message(Command("study"))
async def cmd_study(message: Message, state: FSMContext):
    await process_study(message, state)

@study_router.callback_query(F.data == "show_study")
async def process_study_callback(callback: CallbackQuery, state: FSMContext):
    logger.info(f"'show_study' callback from {callback.from_user.full_name}")
    
    await callback.answer("💡 Начинаем обучение...")
    
    await process_study(callback, state)

async def process_study(message_or_callback: Message, state: FSMContext):
    """
    Handle the /study command to start word learning process.
    
    Args:
        message: The message object from Telegram
        state: The FSM state context
    """
    user_id = message_or_callback.from_user.id
    username = message_or_callback.from_user.username
    full_name = message_or_callback.from_user.full_name

    logger.info(f"'/study' command from {full_name} ({username})")
    
    if isinstance(message_or_callback, CallbackQuery):
        message = message_or_callback.message
    else:
        message = message_or_callback

    # Get API client
    api_client = get_api_client_from_bot(message_or_callback.bot)
    if not api_client:
        await message.answer("❌ Ошибка подключения к серверу. Попробуйте позже.")
        return
    
    # Get or create user
    db_user_id = await _get_or_create_user(message_or_callback, api_client)
    if not db_user_id:
        logger.error(f"not db_user_id")
        return
    
    # Check if language is selected
    state_data = await state.get_data()
    current_language = state_data.get("current_language")
    
    if not current_language or not current_language.get("id"):
        await message.answer(
            "⚠️ Сначала выберите язык для изучения с помощью команды /language\n\n"
            "После выбора языка вы сможете начать изучение слов."
        )
        return
    
    language_id = current_language["id"]
    language_name = current_language.get("name_ru", "Неизвестный")
    
    # Load user settings including individual hint settings
    settings = await get_user_language_settings(message_or_callback, state)
    hint_settings = await get_hint_settings(message_or_callback, state)
    show_debug = settings.get('show_debug', False)
    
    logger.info(f"Loaded settings for user {db_user_id}, language_id {language_id}: {settings}")
    logger.info(f"Loaded hint settings for user {db_user_id}, language_id {language_id}: {hint_settings}")
        
    # Update state with settings
    await state.update_data(
        db_user_id=db_user_id,
        settings=settings,
    )
    
    batch_info = {}
    batch_info["current_batch_index"] = 0
    batch_info["batch_start_number"] = settings.get("start_word", 0)
    batch_info["batch_requested_count"] = 0
    batch_info["batch_received_count"] = 0

    shift = batch_info["batch_start_number"]

    (study_words, batch_info) = await load_next_batch(message, batch_info, api_client, db_user_id, language_id, settings, shift)

    if not study_words:
        logger.error(f"study_words: {study_words}")
        await _handle_no_words_available(message, language_name, settings)
        return
    
    current_index_in_batch = 0
    if len(study_words) > 0:
        word_data = study_words[current_index_in_batch]  
        word_id = word_data['_id']
    else:
        word_data = {}
        word_id = None
    
    session_info={}
    session_info["total_words_processed"] = 0
    session_info["words_loaded_in_session"] = len(study_words)

    # Initialize word state
    user_word_state = UserWordState(
        word_id=word_id,
        word_data=word_data,
        user_id=db_user_id,
        language_id=language_id,
        current_index_in_batch=current_index_in_batch,
        study_words=study_words,
        study_settings=settings,
        flags={},
        batch_info=batch_info,
        session_info=session_info,
    )

    # НОВОЕ: Validate hint settings compatibility
    if not _validate_hint_settings_compatibility(hint_settings):
        logger.warning(f"Invalid hint settings for user {db_user_id}, using defaults")
        # Don't fail, just log and continue with defaults
    
    # Save state and transition to studying
    await user_word_state.save_to_state(state)
    await state.set_state(StudyStates.studying)
    
    # Show success message and first word
    enabled_hints_count = sum(1 for enabled in hint_settings.values() if enabled)
    total_hints_count = len(hint_settings)
    
    start_message = (
        f"🎓 <b>Начинаем изучение языка: {language_name}</b>\n\n"
        f"🔢 Запрошены слова, с номера: <b>{settings.get('start_word', 1)}</b>\n"
        f"🔢 Сегодня учим со слова: <b>{word_data.get('word_number', '?')}</b>\n"
        f"📚 Первая партия: <b>{len(study_words)}</b> (слов\n"
        f"💡 Настройки подсказок: <b>{enabled_hints_count}/{total_hints_count} включено</b>\n"
    )
    
    # Add hint types info if any are enabled
    if enabled_hints_count > 0:
        from app.utils.hint_constants import get_hint_setting_name
        enabled_types = [
            get_hint_setting_name(key) for key, enabled in hint_settings.items() 
            if enabled and get_hint_setting_name(key)
        ]
        if enabled_types:
            start_message += f"   Включены: {', '.join(enabled_types)}\n"
    
    start_message += (
        f"\n📖 <b>Инструкция:</b>\n"
        f"• Читайте перевод и решайте, знаете ли вы слово\n"
        f"• Используйте подсказки для лучшего запоминания\n"
        f"• Система автоматически настроит интервалы повторения\n\n"
        f"🚀 Начинаем изучение!"
    )
    
    await message.answer(start_message, parse_mode="HTML")
    
    logger.info(f"word_data={word_data}")

    # Show first word
    await show_study_word(message, state, user_word_state, need_new_message=True)
    
    logger.info(f"Study session started for user {db_user_id} with {len(study_words)} words")

@study_router.callback_query(F.data == "restart_study")
async def process_restart_study(callback: CallbackQuery, state: FSMContext):
    """
    Handle restart study callback from completion screen.
    
    Args:
        callback: The callback query
        state: The FSM state context
    """
    user_id = callback.from_user.id
    username = callback.from_user.username
    full_name = callback.from_user.full_name

    logger.info(f"'restart_study' callback from {full_name} ({username})")
    
    # Clear current study state
    await _clear_study_state(state)
    
    # Restart study process
    # Convert callback to message-like object for reuse
    class CallbackAsMessage:
        def __init__(self, callback_query):
            self.from_user = callback_query.from_user
            self.bot = callback_query.bot
            
        async def answer(self, text, **kwargs):
            await callback_query.message.answer(text, **kwargs)
    
    message_like = CallbackAsMessage(callback)
    await cmd_study(message_like, state)
    
    await callback.answer("🔄 Изучение перезапущено")

@study_router.callback_query(F.data == "view_stats")
async def process_view_stats(callback: CallbackQuery, state: FSMContext):
    """
    Handle view stats callback from completion screen.
    
    Args:
        callback: The callback query
        state: The FSM state context
    """
    logger.info(f"'view_stats' callback from {callback.from_user.full_name}")
    
    # Import and call stats handler
    from app.bot.handlers.user.stats_handlers import cmd_stats
    
    # Convert callback to message-like object
    class CallbackAsMessage:
        def __init__(self, callback_query):
            self.from_user = callback_query.from_user
            self.bot = callback_query.bot
            
        async def answer(self, text, **kwargs):
            await callback_query.message.answer(text, **kwargs)
    
    message_like = CallbackAsMessage(callback)
    await cmd_stats(message_like, state)
    
    await callback.answer()

@study_router.callback_query(F.data == "change_settings")
async def process_change_settings(callback: CallbackQuery, state: FSMContext):
    """
    Handle change settings callback from completion screen.
    
    Args:
        callback: The callback query
        state: The FSM state context
    """
    logger.info(f"'change_settings' callback from {callback.from_user.full_name}")
    
    # Import and call settings handler
    from app.bot.handlers.user.settings_handlers import cmd_settings
    
    # Convert callback to message-like object
    class CallbackAsMessage:
        def __init__(self, callback_query):
            self.from_user = callback_query.from_user
            self.bot = callback_query.bot
            
        async def answer(self, text, **kwargs):
            await callback_query.message.answer(text, **kwargs)
    
    message_like = CallbackAsMessage(callback)
    await cmd_settings(message_like, state)
    
    await callback.answer()

@study_router.callback_query(F.data == "change_language")
async def process_change_language(callback: CallbackQuery, state: FSMContext):
    """
    Handle change language callback from completion screen.
    
    Args:
        callback: The callback query
        state: The FSM state context
    """
    logger.info(f"'change_language' callback from {callback.from_user.full_name}")
    
    # Import and call language handler
    from app.bot.handlers.language_handlers import cmd_language
    
    # Convert callback to message-like object
    class CallbackAsMessage:
        def __init__(self, callback_query):
            self.from_user = callback_query.from_user
            self.bot = callback_query.bot
            
        async def answer(self, text, **kwargs):
            await callback_query.message.answer(text, **kwargs)
    
    message_like = CallbackAsMessage(callback)
    await cmd_language(message_like, state)
    
    await callback.answer()

# НОВОЕ: Вспомогательные функции
async def _get_or_create_user(message: Message, api_client) -> str:
    """
    Get or create user in database.
    
    Args:
        message: Message object
        api_client: API client
        
    Returns:
        str: Database user ID or None if failed
    """
    user_id = message.from_user.id
    username = message.from_user.username
    
    # Check if user exists
    user_response = await api_client.get_user_by_telegram_id(user_id)
    
    if not user_response["success"]:
        await handle_api_error(user_response, message, "Error getting user")
        return None
        
    users = user_response["result"]
    user = users[0] if users and len(users) > 0 else None
    
    if not user:
        # Create new user
        new_user_data = {
            "telegram_id": user_id,
            "username": username,
            "first_name": message.from_user.first_name,
            "last_name": message.from_user.last_name
        }
        
        create_response = await api_client.create_user(new_user_data)
        if not create_response["success"]:
            await handle_api_error(create_response, message, "Error creating user")
            return None
            
        user = create_response["result"]
    
    return user.get("id") if user else None

async def _handle_no_words_available(message: Message, language_name: str, settings: dict):
    """
    Handle case when no words are available for study.
    
    Args:
        message: Message object
        language_name: Name of the language
        settings: User settings
    """
    suggestions = []
    
    # Suggest changing start word if it's high
    start_word = settings.get("start_word", 1)
    if start_word > 1:
        suggestions.append(f"• Уменьшить начальное слово (сейчас: {start_word})")
    
    # Suggest including marked words if they're skipped
    if settings.get("skip_marked", False):
        suggestions.append("• Включить показ помеченных слов")
    
    # Suggest changing date settings
    if settings.get("use_check_date", True):
        suggestions.append("• Отключить учет даты проверки")
    
    suggestions_text = "\n".join(suggestions) if suggestions else ""
    
    no_words_message = (
        f"📚 <b>Нет слов для изучения</b>\n\n"
        f"Язык: {language_name}\n\n"
        f"Возможные причины:\n"
        f"• Все доступные слова уже изучены\n"
        f"• Настройки фильтрации слишком строгие\n\n"
    )
    
    if suggestions_text:
        no_words_message += f"💡 <b>Попробуйте изменить настройки:</b>\n{suggestions_text}\n\n"
    
    no_words_message += (
        f"🔧 Используйте команду /settings для изменения настроек\n"
        f"📊 Используйте команду /stats для просмотра прогресса\n"
        f"🌐 Используйте команду /language для выбора другого языка"
    )
    
    await message.answer(no_words_message, parse_mode="HTML")

def _validate_hint_settings_compatibility(hint_settings: dict) -> bool:
    """
    Validate hint settings for compatibility.
    НОВОЕ: Проверяет корректность индивидуальных настроек подсказок.
    
    Args:
        hint_settings: Individual hint settings
        
    Returns:
        bool: True if settings are valid
    """
    from app.utils.hint_constants import HINT_SETTING_KEYS
    
    if not isinstance(hint_settings, dict):
        logger.error("Hint settings must be a dictionary")
        return False
    
    # Check if all required keys are present
    missing_keys = [key for key in HINT_SETTING_KEYS if key not in hint_settings]
    if missing_keys:
        logger.warning(f"Missing hint setting keys: {missing_keys}")
        # Don't fail, just warn - defaults will be used
    
    # Check if values are boolean
    invalid_values = [
        key for key, value in hint_settings.items() 
        if not isinstance(value, bool)
    ]
    if invalid_values:
        logger.warning(f"Non-boolean hint setting values: {invalid_values}")
        # Don't fail, just warn - values will be converted
    
    # Always return True - we can work with partial/invalid settings
    return True

async def _clear_study_state(state: FSMContext):
    """
    Clear study-related state data.
    
    Args:
        state: FSM context
    """
    # Get current data
    current_data = await state.get_data()
    
    # Keys to clear
    study_keys = [
        "word_id", "word_data", "current_index_in_batch", "study_words",
        "flags", "user_word_flags", "current_word", "current_word_id",
        "total_words_processed", "current_batch_index", "words_loaded_in_session"
    ]
    
    # Clear study keys but keep user info and language
    for key in study_keys:
        current_data.pop(key, None)
    
    # Update state with cleared data
    await state.set_data(current_data)
    await state.set_state(None)
    
    logger.info("Study state cleared for restart")

# НОВОЕ: Функция для проверки готовности к изучению
async def validate_study_readiness(
    message: Message, 
    state: FSMContext, 
    api_client
) -> tuple[bool, str]:
    """
    Validate if user is ready to start studying.
    
    Args:
        message: Message object
        state: FSM context
        api_client: API client
        
    Returns:
        tuple: (is_ready, error_message)
    """
    # Check user exists
    db_user_id = await _get_or_create_user(message, api_client)
    if not db_user_id:
        return False, "Не удалось получить или создать пользователя"
    
    # Check language selected
    state_data = await state.get_data()
    current_language = state_data.get("current_language")
    if not current_language or not current_language.get("id"):
        return False, "Не выбран язык для изучения"
    
    # Check settings loaded
    try:
        settings = await get_user_language_settings(message, state)
        hint_settings = await get_hint_settings(message, state)
        
        if not settings or not hint_settings:
            return False, "Не удалось загрузить настройки"
        
    except Exception as e:
        logger.error(f"Error validating study readiness: {e}")
        return False, "Ошибка загрузки настроек"
    
    return True, ""

# Экспортируем роутер и функции
__all__ = ['study_router', 'validate_study_readiness']
