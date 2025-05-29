"""
Handlers for word display actions during the study process.
Обработчики для отображения слов в процессе изучения.
"""

from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext

from app.utils.api_utils import get_api_client_from_bot
from app.utils.logger import setup_logger
from app.utils.error_utils import validate_state_data
from app.utils.state_models import UserWordState
from app.utils.word_data_utils import update_word_score
from app.bot.keyboards.study_keyboards import create_word_keyboard
from app.utils.formatting_utils import format_study_word_message, format_used_hints
from app.utils.settings_utils import get_show_hints_setting

# Импортируем централизованные состояния
from app.bot.states.centralized_states import StudyStates

# Создаем роутер для обработчиков отображения слов
display_router = Router()

logger = setup_logger(__name__)


@display_router.callback_query(F.data == "show_word", StudyStates.studying)
async def process_show_word(callback: CallbackQuery, state: FSMContext):
    """
    Process callback when user wants to see the word.
    
    Args:
        callback: The callback query from Telegram
        state: The FSM state context
    """
    user_id = callback.from_user.id
    username = callback.from_user.username
    full_name = callback.from_user.full_name

    logger.info(f"'show_word' 1 callback from {full_name} ({username})")
    
    # Validate state data
    is_valid, state_data = await validate_state_data(
        state, 
        ["current_word"],
        callback,
        "Ошибка: недостаточно данных для показа слова"
    )
    
    if not is_valid:
        logger.error(f"not is_valid")
        await callback.answer("Ошибка: недостаточно данных")
        return
    
    # Get required data
    current_word = state_data["current_word"]
    current_word_id = state_data["current_word_id"]
    db_user_id = state_data["db_user_id"]
    
    # Проверяем, был ли вызван callback с экрана подтверждения (после "Я знаю это слово")
    user_word_state = await UserWordState.from_state(state)
    was_pending_word_know = False
    
    if user_word_state.is_valid():
        was_pending_word_know = user_word_state.get_flag('pending_word_know', False)
        # Сбрасываем флаг, так как пользователь передумал
        if was_pending_word_know:
            user_word_state.remove_flag('pending_word_know')
            user_word_state.remove_flag('pending_next_word')
            await user_word_state.save_to_state(state)
    
    if 'user_word_data' not in current_word:
        current_word['user_word_data'] = {}
        
    current_skipped = current_word['user_word_data'].get('is_skipped', False)

    # Update word score to 0 (not known), but don't mark as skipped
    success, result = await update_word_score(
        callback.bot,
        db_user_id,
        current_word_id,
        score=0,
        word=current_word,
        message_obj=callback,
        is_skipped=current_skipped # оставляем старое значение
    )
    
    if not success:
        logger.error(f"not success")
        return

    current_word['user_word_data']['is_skipped'] = result['is_skipped']
    current_word['user_word_data']['check_interval'] = result['check_interval']
    current_word['user_word_data']['next_check_date'] = result['next_check_date']
    current_word['user_word_data']['score'] = result['score']

    # Get word information
    word_foreign = current_word.get("word_foreign", "N/A")
    transcription = current_word.get("transcription", "")
    
    # Get language info for message formatting
    language_id = current_word.get("language_id")
    api_client = get_api_client_from_bot(callback.bot)
    language_response = await api_client.get_language(language_id)
    
    if not language_response["success"] or not language_response["result"]:
        await callback.answer("Ошибка: язык не найден")
        return
    
    language = language_response["result"]
    
    # Получаем основную информацию для форматирования сообщения
    word_number = current_word.get('word_number', 'N/A')
    translation = current_word.get('translation', '')
    
    # Получаем данные пользователя
    user_word_data = current_word.get("user_word_data", {})

    is_skipped = user_word_data.get("is_skipped", False)
    check_interval = user_word_data.get("check_interval", 0)
    next_check_date = user_word_data.get("next_check_date", None)
    score = user_word_data.get("score", 0)
    
    # Mark the word as shown in the state
    if not user_word_state.is_valid():
        logger.error(f"not user_word_state.is_valid()")
        return

    # Set flag that word has been shown
    user_word_state.set_flag('word_shown', True)

    user_word_state.word_data = current_word
    
    # Save updated state
    await user_word_state.save_to_state(state)
    
    # НОВОЕ: Переходим в состояние просмотра деталей слова
    await state.set_state(StudyStates.viewing_word_details)
    
    # Get used hints
    used_hints = user_word_state.get_flag("used_hints", [])
    
    # Get show_hints setting
    show_hints = await get_show_hints_setting(callback, state)
    
    # Формируем обновленное сообщение
    updated_message = format_study_word_message(
        language.get('name_ru'),
        language.get('name_foreign'),
        word_number,
        translation,
        is_skipped,
        score,
        check_interval,
        next_check_date,
        show_word=True,
        word_foreign=word_foreign,
        transcription=transcription
    )
    
    # Добавляем активные подсказки с помощью новой функции
    hint_text = await format_used_hints(
        bot=callback.bot,
        user_id=user_word_state.user_id,
        word_id=user_word_state.word_id,
        current_word=current_word,
        used_hints=used_hints,
        include_header=True
    )
    
    updated_message += hint_text
    
    # Create updated keyboard 
    keyboard = create_word_keyboard(
        current_word, 
        word_shown=True, 
        show_hints=show_hints,
        used_hints=used_hints
    )
    
    # Если пользователь нажал "Ой, все-таки не знаю" и возвращается к слову
    if was_pending_word_know:
        # Отправляем сообщение о возврате к слову, НЕ редактируя предыдущее сообщение
        await callback.message.answer(
            "⬅️ Возвращаемся к изучению слова. Вы можете посмотреть его и использовать подсказки.",
            parse_mode="HTML"
        )
        
        # Отправляем новое сообщение с информацией о слове
        await callback.message.answer(
            updated_message,
            reply_markup=keyboard,
            parse_mode="HTML"
        )
    else:
        # Если пользователь нажал "Показать слово" с основного экрана изучения -
        # обновляем существующее сообщение
        try:
            await callback.message.edit_text(
                updated_message,
                reply_markup=keyboard,
                parse_mode="HTML"
            )
        except Exception as e:
            logger.error(f"Error editing message in process_show_word: {e}", exc_info=True)
            # Если не удалось обновить сообщение, отправляем новое
            await callback.message.answer(
                updated_message,
                reply_markup=keyboard,
                parse_mode="HTML"
            )
    
    await callback.answer()


@display_router.callback_query(F.data == "show_word", StudyStates.confirming_word_knowledge)
async def process_show_word_from_confirmation(callback: CallbackQuery, state: FSMContext):
    """
    Process show_word callback from the confirmation state.
    This handles when user clicks "Ой, все-таки не знаю" after confirming they know the word.
    
    Args:
        callback: The callback query from Telegram
        state: The FSM state context
    """
    logger.info(f"'show_word' callback from confirmation state from {callback.from_user.full_name}")
    
    # НОВОЕ: Возвращаемся в основное состояние изучения перед обработкой
    await state.set_state(StudyStates.studying)
    
    # Используем основной обработчик show_word
    await process_show_word(callback, state)
    