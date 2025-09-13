"""
Handlers for word navigation actions during the study process.
Обработчики для навигации между словами в процессе изучения.
"""

from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext
from datetime import datetime

from app.utils.api_utils import get_api_client_from_bot
from app.utils.logger import setup_logger
from app.utils.state_models import UserWordState
from app.bot.handlers.study.study_words import show_study_word, load_next_batch
from app.utils.callback_constants import CallbackData
from app.bot.states.centralized_states import StudyStates
from app.utils.statistics_utils import load_progress, update_daily_statistics, show_today_statistics, show_monthly_statistics, update_daily_first_finish_statistics

logger = setup_logger(__name__)

# Создаем роутер для навигационных действий
navigation_router = Router()


@navigation_router.callback_query(F.data == CallbackData.NEXT_WORD, StudyStates.viewing_word_details)
@navigation_router.callback_query(F.data == CallbackData.NEXT_WORD, StudyStates.studying)
async def process_next_word(callback: CallbackQuery, state: FSMContext):
    """
    Process 'Next word' action.
    
    Args:
        callback: The callback query
        state: FSM context
    """
    logger.info(f"'next_word' action from {callback.from_user.full_name}")
    
    # Get current word state
    user_word_state = await UserWordState.from_state(state)
    
    if not user_word_state.is_valid():
        await callback.answer("❌ Неверное состояние изучения")
        logger.error(f"Invalid user_word_state: {user_word_state}")
        return
    
    state_data = await state.get_data()

    settings = state_data.get("settings", {})
    show_debug = settings.get("show_debug", False)
    show_charts = settings.get("show_charts", False)

    # перезапуск сессии
    last_action_date_time = state_data.get("last_action_date_time", None)
    logger.info(f"last_action_date_time: {last_action_date_time}")

    progress = state_data.get("progress", {})
    progress_updated = False

    if last_action_date_time is not None:
        last_action_date_time = datetime.fromisoformat(last_action_date_time)

        delta_days = (datetime.now().date() - last_action_date_time.date()).days
        delta_hours = (datetime.now() - last_action_date_time).seconds // 3600

        reset_session_days = settings.get("reset_session_days", 1)
        reset_session_hours = settings.get("reset_session_hours", 6)

        logger.info(f"delta_days: {delta_days}, delta_hours: {delta_hours}")
        logger.info(f"reset_session_days: {reset_session_days}, reset_session_hours: {reset_session_hours}")

        if (delta_days >= reset_session_days) and (delta_hours >= reset_session_hours):
            progress = await load_progress(callback, state)
            progress_updated = True

            # обновляем дневную статистику
            await update_daily_statistics(callback, state)

            if show_charts:
                await show_today_statistics(callback, state)

            await callback.message.answer(f"Предыдущее изучение было {delta_days} (дней) назад. Рекомендуется перезапустить сессию командой /study и повторить слова с начала.")

    last_action_date_time = datetime.now().isoformat()
    await state.update_data(last_action_date_time=last_action_date_time)
    logger.info(f"new last_action_date_time: {last_action_date_time}")

    # показываем месячную статистику
    if show_debug:
        await show_monthly_statistics(callback, state)
        await show_today_statistics(callback, state)

    # переход к новым словам
    words_studied = progress.get('words_studied', 0)
    logger.info(f"words_studied: {words_studied}")

    current_word_number = user_word_state.word_data.get('word_number', None)
    logger.info(f"current_word_number: {current_word_number}")
    
    if (current_word_number is not None) and (current_word_number >= words_studied):
        if not progress_updated:
            progress = await load_progress(callback, state)
            progress_updated = True

            await update_daily_statistics(callback, state)

            await update_daily_first_finish_statistics(callback, state)

            if show_charts:
                await show_today_statistics(callback, state)

        unknown_count = progress.get('words_studied', 0) - progress.get('words_known', 0) - progress.get('words_skipped', 0)
        unknown_limit_new_words = settings.get("unknown_limit_new_words", 10)
        logger.info(f"unknown_count: {unknown_count}, unknown_limit_new_words: {unknown_limit_new_words}")

        if (unknown_count >= unknown_limit_new_words):
            await callback.message.answer(
                f"Осталось неизвестных слов: {unknown_count}\n" +
                f"Лимит неизвестных слов: {unknown_limit_new_words}\n\n" +
                "Перед изучением новых слов - рекомендуется перезапустить сессию командой /study и повторить слова с начала."
            )
        else:
            if (unknown_count == 0):
                await callback.message.answer(
                    f"Поздравляем!\n" +
                    f"Вы выучили все пройденные слова: {progress.get('words_studied', 0)} (пропущенных: {progress.get('words_skipped', 0)})\n" +
                    "Так держать! Продолжайте в том же духе!"
                )
            else:
                await callback.message.answer(
                    f"Вы переходите к новому слову\n" +
                    f"Текущая статистика:\n" +
                    f"* Изучено: {progress.get('words_studied', 0)}\n" +
                    f"* Известных: {progress.get('words_known', 0)}\n" +
                    f"* Неизвестных: {unknown_count}\n" +
                    f"* Пропущенных: {progress.get('words_skipped', 0)}\n" +
                    f"Лимит неизвестных слов: {unknown_limit_new_words}\n"
                )

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


@navigation_router.callback_query(F.data == CallbackData.CONFIRM_NEXT_WORD, StudyStates.confirming_word_knowledge)
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


@navigation_router.callback_query(F.data == CallbackData.BACK_TO_STUDY_FROM_ADMIN)
async def process_back_to_study_from_admin(callback: CallbackQuery, state: FSMContext):
    """
    Обработчик возврата к изучению слов из админ-режима редактирования.
    
    Args:
        callback: The callback query
        state: FSM context
    """
    logger.info(f"'back_to_study_from_admin' callback from {callback.from_user.full_name}")
    
    await state.set_state(StudyStates.studying)

    # Показываем текущее слово изучения
    user_word_state = await UserWordState.from_state(state)
    
    if user_word_state.is_valid():
        await show_study_word(callback, state, user_word_state, need_new_message=True)
        await callback.answer("⬅️ Возвращаемся к изучению")
    else:
        logger.error("Invalid study state after restoration")
        await callback.answer("❌ Ошибка восстановления состояния изучения")
        await callback.message.answer(
            "❌ Ошибка восстановления состояния изучения.\n"
            "Используйте команду /study для начала изучения заново."
        )


async def _handle_batch_completion(
    callback: CallbackQuery, 
    state: FSMContext, 
    user_word_state: UserWordState
):
    """
    Handle completion of current word batch using centralized loading.
    
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
                logger.error(f"Error handling batch completion")
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
