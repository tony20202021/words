"""
Handlers for utility word actions during the study process.
Обработчики для утилитарных действий со словами (переключение пропуска и т.д.).
"""

from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext

from app.utils.logger import setup_logger
from app.utils.state_models import UserWordState
from app.bot.handlers.study.study_words import show_study_word
from app.utils.callback_constants import CallbackData
from app.utils.word_data_utils import ensure_user_word_data

logger = setup_logger(__name__)

# Создаем роутер для утилитарных действий
utility_router = Router()

@utility_router.callback_query(F.data == CallbackData.TOGGLE_WORD_SKIP)
async def process_toggle_word_skip(callback: CallbackQuery, state: FSMContext):
    """
    Process toggle word skip status.
    FIXED: Uses centralized utilities for data updates.
    
    Args:
        callback: The callback query
        state: FSM context
    """
    logger.info(f"'toggle_word_skip' action from {callback.from_user.full_name}")

    # Get current word state
    user_word_state = await UserWordState.from_state(state)
    
    if not user_word_state.is_valid() or not user_word_state.has_more_words():
        await callback.answer("❌ Нет активного слова")
        return
    
    # Get current word
    current_word = user_word_state.get_current_word()
    if not current_word:
        await callback.answer("❌ Ошибка получения текущего слова")
        return
    
    # Toggle skip status
    user_word_data = current_word.get("user_word_data", {})
    current_skip_status = user_word_data.get("is_skipped", False)
    new_skip_status = not current_skip_status
    
    # Update word data using centralized utility
    try:
        update_data = {"is_skipped": new_skip_status}

        success, result = await ensure_user_word_data(
            bot=callback.bot,
            user_id=user_word_state.user_id,
            word_id=user_word_state.word_id,
            update_data=update_data,
            word=current_word,
            message_obj=callback
        )

        if success:
            # Update local word data
            if "user_word_data" not in current_word:
                current_word["user_word_data"] = {}
            current_word["user_word_data"]["is_skipped"] = new_skip_status
            
            # Save state
            await user_word_state.save_to_state(state)
            
            # Refresh display using centralized function
            await show_study_word(callback, state, user_word_state, need_new_message=False)
            
            status_text = "пропускать" if new_skip_status else "показывать"
            await callback.answer(f"✅ Слово будет {status_text}")
            
        else:
            await callback.answer("❌ Ошибка изменения статуса слова")
            
    except Exception as e:
        logger.error(f"Error toggling word skip status: {e}")
        await callback.answer("❌ Ошибка изменения статуса слова")
