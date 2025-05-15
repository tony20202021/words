"""
Functions for getting and displaying words in the study process.
"""

from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from app.utils.api_utils import get_api_client_from_bot
from app.utils.logger import setup_logger
from app.utils.error_utils import handle_api_error
from app.utils.state_models import UserWordState
from app.bot.keyboards.study_keyboards import create_word_keyboard
from app.utils.formatting_utils import format_study_word_message
from app.utils.settings_utils import get_user_language_settings
from app.utils.hint_constants import get_hint_key, get_hint_name, get_hint_icon
from app.utils.formatting_utils import format_study_word_message, format_active_hints

logger = setup_logger(__name__)

async def get_words_for_study(message: Message, state: FSMContext, user_id: str, language_id: str, study_settings: dict):
    """
    Get words for study based on settings using the API's get_study_words method.
    
    Args:
        message: The message object from Telegram
        state: The FSM state context
        user_id: User ID in database
        language_id: Language ID
        study_settings: Study settings dictionary
        
    Returns:
        bool: True if words were retrieved successfully, False otherwise
    """
    # Get API client
    api_client = get_api_client_from_bot(message.bot)
    
    # Parameters for request
    study_params = {
        "start_word": study_settings.get("start_word", 1),
        "skip_marked": study_settings.get("skip_marked", False),
        "use_check_date": study_settings.get("use_check_date", True)
    }
    
    # Add limit to parameters
    limit = 100  # or other suitable value
    
    # Save show_hints setting to state
    show_hints = study_settings.get("show_hints", True)
    await state.update_data(show_hints=show_hints)
    
    # Log request details
    logger.info(
        f"Requesting study words: user_id={user_id}, language_id={language_id}, " 
        f"params={study_params}, limit={limit}, show_hints={show_hints}"
    )
    
    try:
        # Request words
        words_response = await api_client.get_study_words(
            user_id, 
            language_id, 
            params=study_params,
            limit=limit,
        )
        
        # Log response status
        logger.info(f"Study words API response: success={words_response['success']}, status={words_response['status']}")
        
        # Handle 404 error (no progress)
        if not words_response["success"] and words_response["status"] == 404:
            logger.warning(f"Got 404 response, user progress not found. Trying fallback to get_words_by_language")
            
            await message.answer(
                "⚠️ Для этого языка еще нет прогресса. Начинаем с первого слова."
            )
            
            # Try to get words without progress
            words_response = await api_client.get_words_by_language(
                language_id, 
                skip=0, 
                limit=limit,
            )
            
            logger.info(f"Fallback API response: success={words_response['success']}, status={words_response['status']}")
        
        # Handle API errors
        if not words_response["success"]:
            await handle_api_error(
                words_response, 
                message, 
                "Error getting study words",
                "Ошибка при получении слов"
            )
            return False
        
        # Get study words from response
        study_words = words_response["result"]
        
        # Логируем количество полученных слов
        if study_words:
            logger.info(f"Retrieved {len(study_words)} words for study from API")
        else:
            logger.warning("No words received from API")
        
        # Check if we have words
        if not study_words or len(study_words) == 0:
            logger.warning(f"No words found for study with settings: {study_params}")
            
            await message.answer(
                "⚠️ Нет доступных слов для изучения с текущими настройками.\n"
                "Попробуйте изменить настройки в меню /settings."
            )
            return False
        
        # Create UserWordState and save to FSM state
        user_word_state = UserWordState(
            word_id=None,  # Will be set when accessing first word
            word_data=None,  # Will be set when accessing first word
            user_id=user_id,
            language_id=language_id,
            current_study_index=0,
            study_words=study_words,
            study_settings=study_settings  # Save full study settings including show_hints
        )
        
        # If we have words, set current word
        if user_word_state.has_more_words():
            current_word = user_word_state.get_current_word()
            
            # Find word_id in various fields
            for id_field in ["_id", "id", "word_id"]:
                if id_field in current_word and current_word[id_field]:
                    user_word_state.word_id = current_word[id_field]
                    break
                    
            user_word_state.word_data = current_word
        
        # Save to state
        await user_word_state.save_to_state(state)
        
        # Show first word
        await show_study_word(message, state)
        return True
        
    except Exception as e:
        logger.error(f"Error getting words for study: {e}", exc_info=True)
        
        await message.answer(
            f"❌ Ошибка при получении слов для изучения: {str(e)}"
        )
        return False

async def show_study_word(message_obj, state: FSMContext):
    """
    Показать слово для изучения.
    
    Args:
        message_obj: Объект сообщения или callback
        state: Контекст состояния FSM
    """
    # Получаем данные слова из состояния
    state_data = await state.get_data()
    user_word_state = await UserWordState.from_state(state)
    
    if not user_word_state.is_valid():
        # Некорректные данные в состоянии
        await message_obj.answer("❌ Ошибка: недостаточно данных для отображения слова.")
        return
    
    if not user_word_state.has_more_words():
        # Нет слов для изучения
        await message_obj.answer(
            "📝 Вы изучили все доступные слова! Выберите другие параметры с помощью команды /settings."
        )
        return
    
    # Текущее слово
    current_word = user_word_state.get_current_word()
    
    # Проверяем наличие флага показа слова
    word_shown = user_word_state.get_flag("word_shown", False)
    
    # Получаем настройку отображения подсказок из состояния
    settings = await get_user_language_settings(message_obj, state)
    show_hints = settings.get("show_hints", True)
    
    # Получаем список активных подсказок
    active_hints = user_word_state.get_flag("active_hints", [])
    
    # Получаем список использованных подсказок
    used_hints = user_word_state.get_flag("used_hints", [])
    
    # Проверяем, был ли это callback или сообщение
    is_callback = isinstance(message_obj, CallbackQuery)
    
    # Формируем сообщение для отображения слова
    language_name_ru = current_word.get("language_name_ru", "")
    language_name_foreign = current_word.get("language_name_foreign", "")
    
    # Если информация о языке не найдена в слове, пытаемся получить из состояния
    if not language_name_ru or not language_name_foreign:
        current_language = state_data.get("current_language", {})
        language_name_ru = current_language.get("name_ru", "Неизвестный")
        language_name_foreign = current_language.get("name_foreign", "")
    
    # Получаем данные о слове
    word_number = current_word.get("word_number", 0)
    translation = current_word.get("translation", "")
    word_foreign = current_word.get("word_foreign", "")
    transcription = current_word.get("transcription", "")
    
    # Данные пользователя о слове
    user_word_data = current_word.get("user_word_data", {})
    is_skipped = user_word_data.get("is_skipped", False)
    check_interval = user_word_data.get("check_interval", 0)
    next_check_date = user_word_data.get("next_check_date")
    score = user_word_data.get("score", 0)
    
    # Формируем текст сообщения
    message_text = format_study_word_message(
        language_name_ru,
        language_name_foreign,
        word_number,
        translation,
        is_skipped,
        score,
        check_interval,
        next_check_date,
        show_word=word_shown,
        word_foreign=word_foreign,
        transcription=transcription
    )
    
    # Добавляем активные подсказки к сообщению 
    bot = message_obj.bot if hasattr(message_obj, 'bot') else message_obj.message.bot
    hint_text = await format_active_hints(
        bot=bot,
        user_id=user_word_state.user_id,
        word_id=user_word_state.word_id,
        current_word=current_word,
        active_hints=active_hints,
        include_header=True
    )
    
    message_text += hint_text
    
    # Создаем клавиатуру для действий со словом с учетом активных подсказок и использованных подсказок
    keyboard = create_word_keyboard(
        current_word, 
        word_shown=word_shown, 
        show_hints=show_hints,
        active_hints=active_hints,
        used_hints=used_hints
    )
    
    # Отправляем или обновляем сообщение
    if is_callback:
        # Если это callback, обновляем существующее сообщение
        try:
            await message_obj.message.edit_text(
                text=message_text,
                reply_markup=keyboard,
                parse_mode="HTML"
            )
        except Exception as e:
            logger.error(f"Error editing message in show_study_word: {e}", exc_info=True)
            # Если не удалось обновить сообщение, отправляем новое
            await message_obj.message.answer(
                text=message_text,
                reply_markup=keyboard,
                parse_mode="HTML"
            )
    else:
        # Если это сообщение, отправляем новое
        await message_obj.answer(
            text=message_text,
            reply_markup=keyboard,
            parse_mode="HTML"
        )
