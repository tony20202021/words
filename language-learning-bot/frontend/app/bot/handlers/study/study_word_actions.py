"""
Study word actions handlers for Language Learning Bot.
Handles word evaluation and navigation during study process.
FIXED: Proper imports, removed code duplication, improved architecture.
"""

from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext

from app.utils.api_utils import get_api_client_from_bot
from app.utils.logger import setup_logger
from app.utils.error_utils import handle_api_error
from app.utils.word_data_utils import update_word_score, ensure_user_word_data
from app.utils.state_models import UserWordState, StateManager
from app.utils.hint_settings_utils import get_individual_hint_settings  # ИСПРАВЛЕНО: правильный импорт
from app.utils.settings_utils import get_show_debug_setting
from app.utils.formatting_utils import format_study_word_message, format_used_hints
from app.bot.keyboards.study_keyboards import create_adaptive_study_keyboard
from app.bot.handlers.study.study_words import show_study_word, load_next_batch
from app.bot.states.centralized_states import StudyStates
from app.utils.callback_constants import CallbackData

# Создаем роутер для действий со словами
word_actions_router = Router()

logger = setup_logger(__name__)

@word_actions_router.callback_query(F.data == CallbackData.WORD_KNOW, StudyStates.studying)
async def process_word_know(callback: CallbackQuery, state: FSMContext):
    """
    Process 'I know this word' action.
    FIXED: Uses centralized utilities and proper error handling.
    
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
    # await _show_word_result(callback, state, user_word_state, current_word, known=True)
    await show_study_word(callback, state, user_word_state, need_new_message=False)
    
    await callback.answer("✅ Отлично! Слово отмечено как известное")

@word_actions_router.callback_query(F.data == CallbackData.WORD_DONT_KNOW, StudyStates.studying)
async def process_word_dont_know(callback: CallbackQuery, state: FSMContext):
    """
    Process 'I don't know this word' action.
    FIXED: Uses centralized utilities and proper error handling.
    
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

@word_actions_router.callback_query(F.data == CallbackData.SHOW_WORD, StudyStates.studying)
@word_actions_router.callback_query(F.data == CallbackData.SHOW_WORD, StudyStates.confirming_word_knowledge)
async def process_show_word(callback: CallbackQuery, state: FSMContext):
    """
    Process 'Show word' action.
    
    Args:
        callback: The callback query
        state: FSM context
    """
    logger.info(f"'show_word' 2 action from {callback.from_user.full_name}")
    
    # Get current word state
    user_word_state = await UserWordState.from_state(state)
    
    if not user_word_state.is_valid() or not user_word_state.has_more_words():
        await callback.answer("❌ Нет активного слова для показа")
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
    user_word_state.set_flag("word_shown", True)
    
    # Save state and transition
    await user_word_state.save_to_state(state)
    await state.set_state(StudyStates.viewing_word_details)
    
    # Use centralized display function
    await show_study_word(callback, state, user_word_state, need_new_message=False)
    
    await callback.answer("👁️ Показываю слово")

@word_actions_router.callback_query(F.data == CallbackData.NEXT_WORD)
async def process_next_word(callback: CallbackQuery, state: FSMContext):
    """
    Process 'Next word' action.
    FIXED: Improved batch loading logic and error handling.
    
    Args:
        callback: The callback query
        state: FSM context
    """
    logger.info(f"'next_word' action from {callback.from_user.full_name}")
    
    # Get current word state
    user_word_state = await UserWordState.from_state(state)
    
    if not user_word_state.is_valid():
        await callback.answer("❌ Неверное состояние изучения")
        return
    
    # Try to advance to next word
    if user_word_state.advance_to_next_word():
        # Successfully moved to next word
        await user_word_state.save_to_state(state)
        await state.set_state(StudyStates.studying)
        
        # Show next word using centralized function
        await show_study_word(callback, state, user_word_state, need_new_message=True)
        await callback.answer()
        
    else:
        # No more words in current batch, try to load next batch
        await _handle_batch_completion(callback, state, user_word_state)

@word_actions_router.callback_query(F.data == CallbackData.CONFIRM_NEXT_WORD, StudyStates.confirming_word_knowledge)
async def process_confirm_next_word(callback: CallbackQuery, state: FSMContext):
    """
    Process confirmation to move to next word.
    
    Args:
        callback: The callback query
        state: FSM context
    """
    logger.info(f"'confirm_next_word' action from {callback.from_user.full_name}")
    
    # Simply call next word handler
    await process_next_word(callback, state)

@word_actions_router.callback_query(F.data == CallbackData.TOGGLE_WORD_SKIP)
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

# # ИСПРАВЛЕНО: Централизованные вспомогательные функции
# async def _show_word_result(
#     callback: CallbackQuery, 
#     state: FSMContext, 
#     user_word_state: UserWordState, 
#     current_word: dict, 
#     known: bool
# ):
#     """
#     Show word result after evaluation using centralized utilities.
#     FIXED: Removed code duplication, uses proper hint settings.
    
#     Args:
#         callback: The callback query
#         state: FSM context
#         user_word_state: Current word state
#         current_word: Current word data
#         known: Whether word was marked as known
#     """
#     try:
#         # Get individual hint settings using proper import
#         hint_settings = await get_individual_hint_settings(callback, state)
#         show_debug = await get_show_debug_setting(callback, state)
        
#         # Get language info
#         state_data = await state.get_data()
#         current_language = state_data.get("current_language", {})
        
#         # Extract word information
#         word_number = current_word.get("word_number", "?")
#         translation = current_word.get("translation", "Нет перевода")
#         word_foreign = current_word.get("word_foreign", "")
#         transcription = current_word.get("transcription", "")
        
#         # Get updated user word data
#         user_word_data = current_word.get("user_word_data", {})
#         is_skipped = user_word_data.get("is_skipped", False)
#         score = user_word_data.get("score", 0)
#         check_interval = user_word_data.get("check_interval", 0)
#         next_check_date = user_word_data.get("next_check_date")
        
#         # Result message
#         result_emoji = "✅" if known else "📝"
#         result_text = "Отлично! Вы знаете это слово!" if known else "Слово для изучения"
        
#         # Format message using centralized utility
#         message_text = f"{result_emoji} <b>{result_text}</b>\n\n"
        
#         message_text += format_study_word_message(
#             language_name_ru=current_language.get("name_ru", "Неизвестный"),
#             language_name_foreign=current_language.get("name_foreign", ""),
#             word_number=word_number,
#             translation=translation,
#             is_skipped=is_skipped,
#             score=score,
#             check_interval=check_interval,
#             next_check_date=next_check_date,
#             score_changed=True,
#             show_word=True,  # Always show word after evaluation
#             word_foreign=word_foreign,
#             transcription=transcription
#         )
        
#         # Add active hints if any using centralized utility
#         used_hints = user_word_state.get_used_hints()
#         if used_hints:
#             hint_text = await format_used_hints(
#                 bot=callback.bot,
#                 user_id=user_word_state.user_id,
#                 word_id=user_word_state.word_id,
#                 current_word=current_word,
#                 used_hints=used_hints,
#                 include_header=True
#             )
#             message_text += hint_text
        
#         # Add debug info if enabled
#         if show_debug:
#             # Use centralized debug function from study_words
#             from app.bot.handlers.study.study_words import _get_debug_info
#             debug_info = await _get_debug_info(user_word_state, current_word, hint_settings)
#             message_text = debug_info + '\n\n' + message_text
        
#         # Create keyboard using centralized utility
#         keyboard = create_adaptive_study_keyboard(
#             word=current_word,
#             word_shown=True,
#             hint_settings=hint_settings,
#             used_hints=used_hints,
#             current_state=await state.get_state(),
#             pending_confirmation=True
#         )
        
#         # Send message
#         await callback.message.edit_text(
#             message_text,
#             reply_markup=keyboard,
#             parse_mode="HTML"
#         )
        
#     except Exception as e:
#         logger.error(f"Error showing word result: {e}")
#         await callback.message.answer("❌ Ошибка отображения результата")

async def _handle_batch_completion(
    callback: CallbackQuery, 
    state: FSMContext, 
    user_word_state: UserWordState
):
    """
    Handle completion of current word batch using centralized loading.
    FIXED: Uses centralized batch loading logic.
    
    Args:
        callback: The callback query
        state: FSM context
        user_word_state: Current word state
    """
    logger.info(f"Batch completion for user {user_word_state.user_id}")
    
    # Try to load next batch using centralized function
    api_client = get_api_client_from_bot(callback.bot)
    
    try:
        state_data = await state.get_data()
        current_language = state_data.get("current_language", {})
        language_id = current_language.get("id")
        
        if not language_id:
            logger.error("No language_id available for loading next batch")
            return False
        
        settings = user_word_state.study_settings

        batch_info = user_word_state.get_batch_info()
        db_user_id = user_word_state.user_id

        shift = user_word_state.get_next_batch_skip()
        batch_info["current_batch_index"] += 1

        (study_words, batch_info) = await load_next_batch(callback.message, batch_info, api_client, db_user_id, language_id, settings, shift)
        
        if (len(study_words) > 0):

            user_word_state.set_batch_info(batch_info)
            
            success = user_word_state.load_new_batch(study_words)
            if not success:
                logger.error(f"Error handling batch completion: {e}")
                await callback.answer("❌ Ошибка загрузки следующих слов")
                return False

            await user_word_state.save_to_state(state)
            logger.info(f"Successfully loaded next batch: {len(study_words)} words")

            # Batch loaded successfully
            await state.set_state(StudyStates.studying)
            await show_study_word(callback, state, user_word_state, need_new_message=True)
            
            # Get batch info for user feedback
            batch_info = user_word_state.get_batch_info()
            await callback.answer(f"📚 Загружена партия #{batch_info['current_batch_index']}")
            return
        
        # No more words available - use centralized completion handler
        from app.bot.handlers.study.study_words import handle_no_more_words
        await handle_no_more_words(callback, state, user_word_state)
        await callback.answer("🎉 Изучение завершено!")
        
    except Exception as e:
        logger.error(f"Error handling batch completion: {e}")
        await callback.answer("❌ Ошибка загрузки следующих слов")

# НОВОЕ: Utility function for word action validation
async def _validate_word_action(
    callback: CallbackQuery,
    user_word_state: UserWordState,
    action_name: str
) -> tuple[bool, dict]:
    """
    Validate word action prerequisites.
    
    Args:
        callback: The callback query
        user_word_state: Current word state
        action_name: Name of the action for logging
        
    Returns:
        tuple: (is_valid, current_word)
    """
    if not user_word_state.is_valid():
        await callback.answer("❌ Неверное состояние изучения")
        logger.error(f"Invalid word state for {action_name}")
        return False, None
    
    if not user_word_state.has_more_words():
        await callback.answer("❌ Нет слов для изучения")
        logger.error(f"No words available for {action_name}")
        return False, None
    
    current_word = user_word_state.get_current_word()
    if not current_word:
        await callback.answer("❌ Ошибка получения текущего слова")
        logger.error(f"No current word for {action_name}")
        return False, None
    
    return True, current_word

# НОВОЕ: Centralized word data update function
async def _update_word_data_safely(
    callback: CallbackQuery,
    user_word_state: UserWordState,
    current_word: dict,
    update_data: dict
) -> bool:
    """
    Safely update word data with error handling.
    
    Args:
        callback: The callback query
        user_word_state: Current word state
        current_word: Current word data
        update_data: Data to update
        
    Returns:
        bool: True if successful
    """
    try:
        success, result = await ensure_user_word_data(
            bot=callback.bot,
            user_id=user_word_state.user_id,
            word_id=user_word_state.word_id,
            update_data=update_data,
            word=current_word,
            message_obj=callback
        )
        
        if success and result:
            # Update local word data
            if "user_word_data" not in current_word:
                current_word["user_word_data"] = {}
            current_word["user_word_data"].update(result)
            return True
        
        return False
        
    except Exception as e:
        logger.error(f"Error updating word data: {e}")
        return False

# Export router
__all__ = ['word_actions_router']
