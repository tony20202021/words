"""
Handlers for word evaluation actions during the study process.
Обработчики для оценки слов в процессе изучения (знаю/не знаю).
ОБНОВЛЕНО: Добавлена поддержка автоматической загрузки следующих партий.
"""

from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext

from app.utils.logger import setup_logger
from app.utils.state_models import UserWordState
from app.utils.word_data_utils import update_word_score
from app.bot.states.centralized_states import StudyStates
from app.utils.callback_constants import CallbackData
from app.bot.handlers.study.study_words import show_study_word
from app.utils.hint_settings_utils import get_individual_hint_settings
from app.utils.admin_utils import is_user_admin
from app.utils.formatting_utils import format_study_word_message, format_used_hints
from app.bot.keyboards.study_keyboards import create_adaptive_study_keyboard
from app.utils.settings_utils import get_show_debug_setting

logger = setup_logger(__name__)

# Создаем роутер для обработчиков оценки слов
evaluation_router = Router()
    
@evaluation_router.callback_query(F.data == CallbackData.WORD_KNOW, StudyStates.studying)
async def process_word_know(callback: CallbackQuery, state: FSMContext):
    """
    Process 'I know this word' action.
    
    Args:
        callback: The callback query
        state: FSM context
    """
    logger.info(f"'word_know' action from {callback.from_user.full_name}")
    
    # Get current word state
    user_word_state = await UserWordState.from_state(state)
    data = await state.get_data()
    logger.info(f"data {data}")
    
    if not user_word_state.is_valid() or not user_word_state.has_more_words():
        await callback.answer("❌ Нет активного слова для оценки")
        return
    
    # Get current word
    current_word = user_word_state.get_current_word()
    if not current_word:
        await callback.answer("❌ Ошибка получения текущего слова")
        return
    
    # Update word score using centralized utility
    success, result = await update_word_score(
        bot=callback.bot,
        user_id=user_word_state.user_id,
        word_id=user_word_state.word_id,
        score=1,  # Known word
        word=current_word,
        message_obj=callback
    )
    
    if not success:
        await callback.answer("❌ Ошибка обновления оценки слова")
        return
    
    # Update local word data
    if "user_word_data" not in current_word:
        current_word["user_word_data"] = {}
    current_word["user_word_data"].update(result or {})
    current_word["user_word_data"]["score"] = 1
    
    # Mark word as processed and set flags
    user_word_state.mark_word_as_processed()
    user_word_state.set_flag("word_shown", True)
    user_word_state.set_flag("pending_next_word", True)
    user_word_state.set_flag("pending_word_know", True)
    
    # Save state and transition
    await user_word_state.save_to_state(state)
    await state.set_state(StudyStates.confirming_word_knowledge)
    
    # Show word result
    await show_study_word(callback, state, user_word_state, need_new_message=False)
    
    await callback.answer("✅ Отлично! Слово отмечено как известное")


@evaluation_router.callback_query(F.data == CallbackData.WORD_DONT_KNOW, StudyStates.studying)
async def process_word_dont_know(callback: CallbackQuery, state: FSMContext):
    """
    Process 'I don't know this word' action.
    
    Args:
        callback: The callback query
        state: FSM context
    """
    logger.info(f"'word_dont_know' action from {callback.from_user.full_name}")
    
    # Get current word state
    user_word_state = await UserWordState.from_state(state)
    
    if not user_word_state.is_valid() or not user_word_state.has_more_words():
        await callback.answer("❌ Нет активного слова для оценки")
        return
    
    # Get current word
    current_word = user_word_state.get_current_word()
    if not current_word:
        await callback.answer("❌ Ошибка получения текущего слова")
        return
    
    # Update word score using centralized utility
    success, result = await update_word_score(
        bot=callback.bot,
        user_id=user_word_state.user_id,
        word_id=user_word_state.word_id,
        score=0,  # Unknown word
        word=current_word,
        message_obj=callback
    )
    
    if not success:
        await callback.answer("❌ Ошибка обновления оценки слова")
        return
    
    # Update local word data
    if "user_word_data" not in current_word:
        current_word["user_word_data"] = {}

    current_word["user_word_data"].update(result or {})
    current_word["user_word_data"]["score"] = 0
    
    # Mark word as processed and set flags
    user_word_state.set_current_word(current_word)
    user_word_state.mark_word_as_processed()
    user_word_state.set_flag("word_shown", True)
    user_word_state.set_flag("pending_next_word", True)
    user_word_state.set_flag("pending_word_know", False)
    
    # Save state and transition
    await user_word_state.save_to_state(state)
    await state.set_state(StudyStates.viewing_word_details)
    
    # Show word result
    await _show_word_result(callback, state, user_word_state, current_word, known=False)
    
    await callback.answer("📝 Слово отмечено как неизвестное")


async def _show_word_result(
    callback: CallbackQuery, 
    state: FSMContext, 
    user_word_state: UserWordState, 
    current_word: dict, 
    known: bool
):
    """
    Show word result after evaluation using centralized utilities.
    FIXED: Removed code duplication, uses proper hint settings.
    
    Args:
        callback: The callback query
        state: FSM context
        user_word_state: Current word state
        current_word: Current word data
        known: Whether word was marked as known
    """
    try:
        # Get individual hint settings using proper import
        hint_settings = await get_individual_hint_settings(callback, state)
        show_debug = await get_show_debug_setting(callback, state)
        
        # НОВОЕ: Проверяем статус администратора для клавиатуры
        is_admin = await is_user_admin(callback, state)
        
        # Get language info
        state_data = await state.get_data()
        current_language = state_data.get("current_language", {})
        
        # Extract word information
        word_number = current_word.get("word_number", "?")
        translation = current_word.get("translation", "Нет перевода")
        word_foreign = current_word.get("word_foreign", "")
        transcription = current_word.get("transcription", "")
        
        # Get updated user word data
        user_word_data = current_word.get("user_word_data", {})
        is_skipped = user_word_data.get("is_skipped", False)
        score = user_word_data.get("score", 0)
        check_interval = user_word_data.get("check_interval", 0)
        next_check_date = user_word_data.get("next_check_date")
        
        # Result message
        result_emoji = "✅" if known else "📝"
        result_text = "Отлично! Вы знаете это слово!" if known else "Слово для изучения"
        
        # Format message using centralized utility
        message_text = f"{result_emoji} <b>{result_text}</b>\n\n"
        
        message_text += format_study_word_message(
            language_name_ru=current_language.get("name_ru", "Неизвестный"),
            language_name_foreign=current_language.get("name_foreign", ""),
            word_number=word_number,
            translation=translation,
            is_skipped=is_skipped,
            score=score,
            check_interval=check_interval,
            next_check_date=next_check_date,
            score_changed=True,
            show_word=True,  # Always show word after evaluation
            word_foreign=word_foreign,
            transcription=transcription
        )
        
        # Add active hints if any using centralized utility
        used_hints = user_word_state.get_used_hints()
        if used_hints:
            hint_text = await format_used_hints(
                bot=callback.bot,
                user_id=user_word_state.user_id,
                word_id=user_word_state.word_id,
                current_word=current_word,
                used_hints=used_hints,
                include_header=True
            )
            message_text += hint_text
        
        # Add debug info if enabled
        if show_debug:
            # Use centralized debug function from study_words
            from app.bot.handlers.study.study_words import _get_debug_info
            debug_info = await _get_debug_info(state, user_word_state, hint_settings, is_admin)
            message_text = debug_info + '\n\n' + message_text
        
        # Create keyboard using centralized utility (ОБНОВЛЕНО: передаем is_admin)
        keyboard = create_adaptive_study_keyboard(
            word=current_word,
            word_shown=True,
            hint_settings=hint_settings,
            used_hints=used_hints,
            current_state=await state.get_state(),
            is_admin=is_admin,  # НОВОЕ: Передаем статус админа
        )
        
        # Send message
        await callback.message.edit_text(
            message_text,
            reply_markup=keyboard,
            parse_mode="HTML"
        )
        
    except Exception as e:
        logger.error(f"Error showing word result: {e}")
        await callback.message.answer("❌ Ошибка отображения результата")
