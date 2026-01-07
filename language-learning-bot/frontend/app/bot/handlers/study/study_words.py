"""
Study words handlers for Language Learning Bot.
Handles word display and navigation during study process.
FIXED: Proper imports, removed code duplication, improved architecture.
UPDATED: Added admin check for showing admin edit button.
UPDATED: Added writing images support in keyboard creation.
"""

import asyncio
from typing import Dict, List, Optional, Any
import json
import traceback

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, BufferedInputFile
from aiogram.fsm.context import FSMContext

from app.utils.logger import setup_logger
from app.utils.formatting_utils import format_study_word_message
from app.utils.state_models import UserWordState, StateManager
from app.utils.settings_utils import get_user_language_settings, is_writing_images_enabled
from app.utils.hint_settings_utils import get_individual_hint_settings
from app.utils.admin_utils import is_user_admin
from app.bot.keyboards.study_keyboards import create_adaptive_study_keyboard
from app.bot.states.centralized_states import StudyStates
from app.utils.formatting_utils import MAX_MESSAGE_LENGTH
from app.utils.api_utils import get_api_client_from_bot

# Создаем роутер для отображения слов
word_display_router = Router()

logger = setup_logger(__name__)

BATCH_LIMIT = 100

async def get_sounds_files(bot, sounds):
    """
    Get sound files from API and convert them to BufferedInputFile for Telegram.
    
    Args:
        bot: Bot instance
        sounds: JSON string with sound file paths
        
    Returns:
        List of BufferedInputFile objects ready to send to Telegram
    """
    api_client = get_api_client_from_bot(bot)

    sounds_info = json.loads(sounds)
    
    result = []
    # Sort keys to ensure consistent order (sound_1, sound_2, sound_3, etc.)
    sorted_keys = sorted(sounds_info.keys())
    for index, key in enumerate(sorted_keys):
        file_path = sounds_info[key]
        logger.debug(f"Processing sound {index} (key={key}): file_path={file_path}")
        sound_response = await api_client.get_sound_file(file_path)
        if not sound_response["success"]:
            logger.error(f"Failed to get sound file ({file_path}): {sound_response}")
            continue
        
        # sound_response["result"] contains binary data (bytes)
        sound_bytes = sound_response["result"]
        if not sound_bytes:
            logger.warning(f"Empty sound data for {file_path}")
            continue
        
        # Create filename using key if it's in format sound_N, otherwise use index
        if key.startswith('sound_') and key[6:].isdigit():
            filename = f"{key}.mp3"
        else:
            filename = f"sound_{index+1}.mp3"
        logger.info(f"Creating BufferedInputFile with filename={filename} for index={index}, key={key}")
        
        # Create BufferedInputFile for Telegram
        input_file = BufferedInputFile(
            file=sound_bytes,
            filename=filename
        )
        result.append(input_file)

    return result


async def format_full_message(
    language_name_ru, 
    language_name_foreign, 
    word_number, 
    translation, 
    is_skipped, 
    score,
    check_interval, 
    next_check_date,
    score_changed=False,
    show_word=False,
    show_radicals=False,
    show_references=False,
    show_tones=False,
    show_sounds=False,
    word_foreign=None,
    transcription=None,
    radicals=None,
    references=None,
    tones=None,
    sounds=None,
    show_big=False,
    show_check_date=True,
    words_studied=0,
    words_for_today=0,
    session_processed=0,
    total_words=0,
    current_state=None,
    used_hints=None,
    message_or_callback=None,
    user_word_state=None,
    current_word=None,
    show_debug=False,
    state=None,
    hint_settings=None,
    is_admin=False,
    show_writing_images=False,
):
    bot = message_or_callback.bot if hasattr(message_or_callback, 'bot') else message_or_callback.message.bot
        
    sounds_files = []
    if bot and sounds and show_sounds:
        sounds_files = await get_sounds_files(
            bot=bot,
            sounds=sounds,
        )

    # Format the main message
    messages = format_study_word_message(
        language_name_ru=language_name_ru,
        language_name_foreign=language_name_foreign,
        word_number=word_number,
        translation=translation,
        is_skipped=is_skipped,
        score=score,
        check_interval=check_interval,
        next_check_date=next_check_date,
        score_changed=score_changed,
        show_word=show_word,
        show_radicals=show_radicals,
        show_references=show_references,
        show_tones=show_tones,
        show_sounds=show_sounds,
        word_foreign=word_foreign,
        transcription=transcription,
        radicals=radicals,
        references=references,
        tones=tones,
        sounds=sounds,
        sounds_files=sounds_files,
        show_big=show_big,
        show_check_date=show_check_date,
        words_studied=words_studied,
        words_for_today=words_for_today,
        session_processed=session_processed,
        total_words=total_words,
    )
    
    if (current_state == StudyStates.confirming_word_knowledge.state):
        messages[-1]["text"] += f"✅ <b>Отлично! Вы знаете это слово!</b>\n\n"

    # Add active hints to message if any
    if used_hints:
        hint_text = await format_used_hints(
            bot=bot,
            user_id=user_word_state.user_id,
            word_id=user_word_state.word_id,
            current_word=current_word,
            used_hints=used_hints,
            include_header=True
        )
        messages[-1]["text"] += hint_text
    
    # Add debug information if enabled
    if show_debug:
        debug_info = await _get_debug_info(state, user_word_state, hint_settings, is_admin, show_writing_images, show_radicals, show_references, show_tones, show_sounds,)
        messages = [{"type": "text", "text": debug_info}] + messages

    return messages
    

async def show_study_word(
    message_or_callback, 
    state: FSMContext, 
    user_word_state: Optional[UserWordState] = None,
    need_new_message: bool = True
):
    """
    Display current study word with appropriate keyboard.
    
    Args:
        message_or_callback: Message or CallbackQuery object
        state: FSM context
        user_word_state: Current word state (optional)
    """
    # Load user word state if not provided
    if user_word_state is None:
        user_word_state = await UserWordState.from_state(state)
    
    if not user_word_state.is_valid() or not user_word_state.has_more_words():
        await handle_no_more_words(message_or_callback, state, user_word_state)
        return
    
    current_word = user_word_state.get_current_word()
    if not current_word:
        logger.error("No current word available in user_word_state")
        await _send_error_message(message_or_callback, "Ошибка получения текущего слова")
        return
    
    # Get individual hint settings
    hint_settings = await get_individual_hint_settings(message_or_callback, state)
    
    # Get basic settings for debug info
    basic_settings = await get_user_language_settings(message_or_callback, state)
    show_debug = basic_settings.get("show_debug", False)
    show_big = basic_settings.get("show_big", False)
    show_check_date = basic_settings.get("show_check_date", True)
    show_short_captions = basic_settings.get("show_short_captions", True)
    
    # Проверяем статус администратора
    is_admin = await is_user_admin(message_or_callback, state)
    
    show_writing_images = await is_writing_images_enabled(message_or_callback, state)
    show_radicals = basic_settings.get("show_radicals", True)
    show_references = basic_settings.get("show_references", True)
    show_tones = basic_settings.get("show_tones", True)
    show_sounds = basic_settings.get("show_sounds", True)
    
    # Get language info from state
    state_data = await state.get_data()
    current_language = state_data.get("current_language", {})
    
    # Extract word information
    word_number = current_word.get("word_number", "?")
    translation = current_word.get("translation", "Нет перевода")
    word_foreign = current_word.get("word_foreign", "")
    transcription = current_word.get("transcription", "")
    radicals = current_word.get("radicals", "")
    references = current_word.get("references", "")
    tones = current_word.get("tones", "")
    sounds = current_word.get("sounds", "")
    
    # Get user word data
    user_word_data = current_word.get("user_word_data", {})
    is_skipped = user_word_data.get("is_skipped", False)
    score = user_word_data.get("score", 0)
    check_interval = user_word_data.get("check_interval", 0)
    next_check_date = user_word_data.get("next_check_date")
    
    # Check if word should be shown
    word_shown = user_word_state.get_flag("word_shown", False)
    used_hints = user_word_state.get_used_hints()
    
    current_state = await state.get_state()
    score_changed = (current_state == StudyStates.confirming_word_knowledge.state)
    progress = state_data.get("progress", {})

    words_studied = progress.get('words_studied', 0)
    words_for_today = progress.get('words_for_today', 0)
    total_words = progress.get('total_words', 0)
    session_processed = user_word_state.get_session_info().get('total_words_processed', 0)

    messages = await format_full_message(
        language_name_ru=current_language.get("name_ru", "Неизвестный"),
        language_name_foreign=current_language.get("name_foreign", ""),
        word_number=word_number, 
        translation=translation, 
        is_skipped=is_skipped, 
        score=score,
        check_interval=check_interval, 
        next_check_date=next_check_date,
        score_changed=score_changed,
        show_word=word_shown,
        show_radicals=show_radicals,
        show_references=show_references,
        show_tones=show_tones,
        show_sounds=show_sounds,
        word_foreign=word_foreign,
        transcription=transcription,
        radicals=radicals,
        references=references,
        tones=tones,
        sounds=sounds,
        show_big=show_big,
        show_check_date=show_check_date,
        words_studied=words_studied,
        words_for_today=words_for_today,
        session_processed=session_processed,
        total_words=total_words,
        current_state=current_state,
        used_hints=used_hints,
        message_or_callback=message_or_callback,
        user_word_state=user_word_state,
        current_word=current_word,
        show_debug=show_debug,
        state=state,
        hint_settings=hint_settings,
        is_admin=is_admin,
        show_writing_images=show_writing_images,
    )

    keyboard = create_adaptive_study_keyboard(
        word=current_word,
        word_shown=word_shown,
        hint_settings=hint_settings,
        used_hints=used_hints,
        current_state=current_state,
        is_admin=is_admin,
        show_writing_images=show_writing_images,
        show_big=show_big,
        show_short_captions=show_short_captions
    )

    # Send or edit message
    try:
        if isinstance(message_or_callback, CallbackQuery):
            message = message_or_callback.message
        else:
            message = message_or_callback

        # aiogram.exceptions.TelegramBadRequest: Telegram server says - Bad Request: message is too long
        # Separate text messages and audio files
        if (not need_new_message) and (len(messages) == 1):
            await message.edit_text(
                messages[0]["text"],
                reply_markup=keyboard,
                parse_mode="HTML"
            )
        else:
            # Send text messages
            for index, current_message in enumerate(messages):
                if current_message["type"] == "text":
                    # Add keyboard to last message
                    has_keyboard = (index == len(messages) - 1) and keyboard
                    await message.answer(
                        current_message["text"],
                        reply_markup=(keyboard if has_keyboard else None),
                        parse_mode="HTML"
                    )
                elif current_message["type"] == "audio":
                    try:
                        audio_file = current_message["file"]
                        
                        # Log filename if available
                        if hasattr(audio_file, 'filename'):
                            logger.info(f"Sending audio file with filename: {audio_file.filename}")
                        else:
                            logger.info(f"Sending audio file")
                        
                        # Use send_audio with explicit parameters
                        await message.bot.send_voice(
                            chat_id=message.chat.id,
                            voice=audio_file,
                        )
                    except Exception as e:
                        logger.error(f"Error sending sound file: {e}")
    
    except Exception as e:
        logger.error(f"Error displaying study word: {e}")
        logger.error(f"{traceback.format_exc()}")
        await _send_error_message(message_or_callback, "Ошибка отображения слова: " + str(e))

async def handle_no_more_words(
    message_or_callback, 
    state: FSMContext, 
    user_word_state: UserWordState
):
    """
    Handle case when there are no more words to study.
    
    Args:
        message_or_callback: Message or CallbackQuery object
        state: FSM context
        user_word_state: Current word state
    """
    # Transition to completion state
    await StateManager.handle_study_completion(state)
    
    # Get session statistics
    if user_word_state.is_valid():
        session_stats = user_word_state.get_session_statistics()
    else:
        session_stats = {
            'total_words_processed': 0,
            'batches_loaded': 1,
            'words_loaded_in_session': 0
        }
    
    completion_text = (
        "🎉 <b>Поздравляем! Вы изучили все доступные слова!</b>\n\n"
        f"📊 <b>Статистика сессии:</b>\n"
        f"• Обработано слов: {session_stats['total_words_processed']}\n"
        f"• Загружено партий: {session_stats['batches_loaded']}\n"
        f"• Всего слов загружено: {session_stats['words_loaded_in_session']}\n\n"
        f"Что делать дальше?\n"
        f"• Начать изучение заново с другими настройками\n"
        f"• Изменить настройки обучения\n"
        f"• Выбрать другой язык для изучения\n"
        f"• Посмотреть подробную статистику"
    )
    
    # Create completion keyboard
    from app.bot.keyboards.study_keyboards import create_study_completed_keyboard
    keyboard = create_study_completed_keyboard()
    
    try:
        if isinstance(message_or_callback, CallbackQuery):
            await message_or_callback.message.answer(
                completion_text,
                reply_markup=keyboard,
                parse_mode="HTML"
            )
        else:
            await message_or_callback.answer(
                completion_text,
                reply_markup=keyboard,
                parse_mode="HTML"
            )
    except Exception as e:
        logger.error(f"Error displaying completion message: {e}")
        await _send_error_message(message_or_callback, "Ошибка отображения завершения")


async def load_next_batch(message, batch_info, api_client, db_user_id: str, language_id: str, settings: dict, shift):
    batch_info["batch_start_number"] = shift
    show_debug = settings.get('show_debug', False)

    study_words = []
    while ((len(study_words) == 0)
        #    and (user_word_state.total_words_processed < language_id) # TODO - добавить правильное условие, что еще не кончились слова в БД
        ):
        words_response = await _load_study_words(api_client, db_user_id, language_id, settings, batch_info["batch_start_number"], BATCH_LIMIT)

        if not words_response:
            logger.error(f"not words_response")
            return
    
        study_words = words_response["result"]
        batch_info["batch_requested_count"] = BATCH_LIMIT
        batch_info["batch_received_count"] = len(study_words)

        if show_debug:
            debug_message = (
                f"current_batch_index={batch_info['current_batch_index']}\n"
                f"batch_start_number={batch_info['batch_start_number']}\n"
                f"batch_requested_count={batch_info['batch_requested_count']}\n"
                f"batch_received_count={batch_info['batch_received_count']}\n"
            )
            
            await message.answer(debug_message, parse_mode="HTML")

        if len(study_words) > 0:
            break

        batch_info["current_batch_index"] += 1
        batch_info["batch_start_number"] += BATCH_LIMIT
    
    return (study_words, batch_info)

    
async def _load_study_words(api_client, db_user_id: str, language_id: str, settings: dict, shift, limit):
    """
    Load study words based on user settings.
    
    Args:
        api_client: API client
        db_user_id: Database user ID
        language_id: Language ID
        settings: User settings
        
    Returns:
        API response or None if failed
    """
    # Prepare parameters based on settings
    params = {
        "start_word": shift,
        "skip_marked": settings.get("skip_marked", False),
        "use_check_date": settings.get("use_check_date", True)
    }
    
    logger.info(f"Loading study words with params: {params}")
    
    # Load words from API
    words_response = await api_client.get_study_words(
        user_id=db_user_id,
        language_id=language_id,
        params=params,
        limit=limit  # Load first batch
    )
    
    if not words_response["success"]:
        logger.error(f"Failed to load study words: {words_response}")
        return None
    
    return words_response


async def _get_debug_info(
    state: FSMContext,
    user_word_state: UserWordState, 
    hint_settings: Dict[str, bool],
    is_admin: bool = False,
    show_writing_images: bool = False,
    show_radicals: bool = False,
    show_references: bool = False,
    show_tones: bool = False,
    show_sounds: bool = False,    
) -> str:
    """
    Get debug information for display.
    
    Args:
        state: FSM state context
        user_word_state: Current word state
        hint_settings: Individual hint settings
        is_admin: Whether user is admin
        show_writing_images: Whether writing images are enabled (NEW)
        show_radicals: Whether radicals are enabled
        show_references: Whether references are enabled
        show_tones: Whether tones are enabled
        show_sounds: Whether sounds are enabled
    Returns:
        str: Formatted debug information
    """
    if not user_word_state.is_valid():
        return "\n\n🔍 <b>Отладочная информация:</b>\n• Неверное состояние слова\n"
    
    # Validate hint settings
    batch_info = user_word_state.get_batch_info()
    session_info = user_word_state.get_session_info()
    
    # Count enabled/disabled hints
    enabled_hints = sum(1 for enabled in hint_settings.values() if enabled)
    total_hints = len(hint_settings)
    
    current_state = await state.get_state()

    debug_text = (
        f"\n\n🔍 <b>Отладочная информация:</b>\n"
        f"• ID слова: {user_word_state.word_id}\n"
        f"• Номер слова (1-based): #{user_word_state.word_data.get('word_number', '?')}\n"
        f"• Индекс в партии (0-based): #{user_word_state.current_index_in_batch}, len={len(user_word_state.study_words)}\n"
        f"• Партия (0-based): #{batch_info['current_batch_index']}\n"
        f"• batch_start_number (1-based): #{batch_info['batch_start_number']}\n"
        f"• batch_requested_count: {batch_info['batch_requested_count']}\n"
        f"• batch_received_count: {batch_info['batch_received_count']}\n"
        f"• Обработано в сессии: {session_info['total_words_processed']}\n"
        f"• Использовано подсказок: {len(user_word_state.get_used_hints())}\n"
        f"• Настройки подсказок: {enabled_hints}/{total_hints} включено\n"
        f"• Картинки написания: {'Вкл' if show_writing_images else 'Откл'}\n"
        f"• Радикалы: {'Вкл' if show_radicals else 'Откл'}\n"
        f"• Ссылки: {'Вкл' if show_references else 'Откл'}\n"
        f"• Тоны: {'Вкл' if show_tones else 'Откл'}\n"
        f"• Звуки: {'Вкл' if show_sounds else 'Откл'}\n"
        f"• current_state: {current_state}\n"
        f"• is_admin: {'Да' if is_admin else 'Нет'}\n"
    )
    
    # Add enabled hint types
    from app.utils.hint_constants import get_hint_setting_name
    enabled_hint_names = [
        get_hint_setting_name(hint_key) for hint_key, enabled in hint_settings.items() 
        if enabled and get_hint_setting_name(hint_key)
    ]
    if enabled_hint_names:
        debug_text += f"• Включенные подсказки: {', '.join(enabled_hint_names)}\n"
    
    # Add word flags
    flags = user_word_state.flags
    if flags:
        active_flags = [key for key, value in flags.items() if value]
        if active_flags:
            debug_text += f"• Активные флаги: {', '.join(active_flags)}\n"
    
    return debug_text

async def _send_error_message(message_or_callback, error_text: str):
    """
    Send error message to user.
    
    Args:
        message_or_callback: Message or CallbackQuery object
        error_text: Error message text
    """
    try:
        if isinstance(message_or_callback, CallbackQuery):
            await message_or_callback.message.answer(f"❌ {error_text}")
        else:
            await message_or_callback.answer(f"❌ {error_text}")
    except Exception as e:
        logger.error(f"Error sending error message: {e}")

# from typing import List, Dict, Any, Optional
from aiogram.client.bot import Bot

from app.utils.hint_constants import HINT_ORDER, get_hint_key, get_hint_short
from app.utils.word_data_utils import get_hint_text

async def format_used_hints(
    bot: Bot,
    user_id: str,
    word_id: str,
    current_word: Dict[str, Any],
    used_hints: List[str],
    include_header: bool = True
) -> str:
    """
    Форматирует текст для активных подсказок в соответствии с порядком HINT_ORDER.
    
    Args:
        bot: Экземпляр бота Telegram для работы с API
        user_id: ID пользователя
        word_id: ID слова
        current_word: Данные текущего слова
        used_hints: Список подсказок
        include_header: Добавлять ли заголовок "Активные подсказки"
        
    Returns:
        str: Отформатированный текст с активными подсказками
    """
    if not used_hints:
        return ""
    
    result = "📌 Подсказки:\n" if include_header else ""
    
    # Сортируем активные подсказки в соответствии с порядком HINT_ORDER
    sorted_hints = [hint_type for hint_type in HINT_ORDER if hint_type in used_hints]
    
    # Добавляем оставшиеся активные подсказки, если они не включены в HINT_ORDER
    for hint_type in used_hints:
        if hint_type not in sorted_hints:
            sorted_hints.append(hint_type)
    
    # Теперь перебираем отсортированный список активных подсказок
    for active_hint_type in sorted_hints:
        active_hint_key = get_hint_key(active_hint_type)
        active_hint_short = get_hint_short(active_hint_type)        
        
        active_hint_text = await get_hint_text(
            bot, 
            user_id, 
            word_id, 
            active_hint_key, 
            current_word
        )
        
        if active_hint_text:
            result += f"<b>{active_hint_short}:</b>\t{active_hint_text}\n"
    
    return result


# Экспортируем основные функции
__all__ = [
    'show_study_word', 
    'handle_no_more_words',
    'load_next_batch',
]
