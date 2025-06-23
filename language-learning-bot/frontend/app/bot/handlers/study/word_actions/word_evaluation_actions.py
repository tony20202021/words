"""
Handlers for word evaluation actions during the study process.
Обработчики для оценки слов в процессе изучения (знаю/не знаю).
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
    await show_study_word(callback, state, user_word_state, need_new_message=False)
    
    await callback.answer("📝 Слово отмечено как неизвестное")
