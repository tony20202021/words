"""
Study command handlers for Language Learning Bot.
"""

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from app.utils.api_utils import get_api_client_from_bot
from app.utils.logger import setup_logger
from app.utils.state_models import UserWordState
from app.utils.settings_utils import get_user_language_settings
from app.utils.hint_settings_utils import get_individual_hint_settings
from app.bot.states.centralized_states import StudyStates
from app.bot.handlers.study.study_words import show_study_word, load_next_batch
from app.bot.handlers.user.stats_handlers import process_stats
from app.bot.handlers.language_handlers import process_language
from app.utils.user_utils import get_or_create_user, validate_language_selected

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
    db_user_id, user_data = await get_or_create_user(message_or_callback.from_user, api_client)
    if not db_user_id:
        logger.error(f"not db_user_id")
        return
    
    # Check if language is selected
    current_language = await validate_language_selected(state, message_or_callback)
    if not current_language:
        return
    
    language_id = current_language["id"]
    language_name = current_language.get("name_ru", "Неизвестный")
    
    # Load user settings including individual hint settings
    settings = await get_user_language_settings(message_or_callback, state)
    hint_settings = await get_individual_hint_settings(message_or_callback, state)
    
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

    await message.answer("🔄 Загружаем слова...")

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
    await show_study_word(message_or_callback, state, user_word_state, need_new_message=True)
    
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
    await process_study(callback, state)
    
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
    
    await process_stats(callback, state)
    
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
    
    await process_language(callback, state)
    
    await callback.answer()

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

# Экспортируем роутер и функции
__all__ = [
    'study_router', 
]
