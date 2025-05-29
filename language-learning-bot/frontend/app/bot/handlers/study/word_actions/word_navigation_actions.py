"""
Handlers for word navigation actions during the study process.
Обработчики для навигации между словами в процессе изучения.
ОБНОВЛЕНО: Добавлена автоматическая загрузка следующих партий слов.
"""

from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext

from app.utils.api_utils import get_api_client_from_bot
from app.utils.logger import setup_logger
from app.utils.state_models import UserWordState
from app.bot.handlers.study.study_words import show_study_word, load_next_batch
from app.utils.formatting_utils import format_date
from app.utils.settings_utils import get_user_language_settings

# Импортируем централизованные состояния
from app.bot.states.centralized_states import StudyStates

# Создаем роутер для навигационных действий
navigation_router = Router()

logger = setup_logger(__name__)


@navigation_router.callback_query(F.data == "next_word", StudyStates.viewing_word_details)        
async def process_next_word(callback: CallbackQuery, state: FSMContext):
    """
    Process callback to go to the next word without changing score.
    ОБНОВЛЕНО: Поддержка автоматической загрузки следующих партий.
    
    Args:
        callback: The callback query from Telegram
        state: The FSM state context
    """
    user_id = callback.from_user.id
    username = callback.from_user.username
    full_name = callback.from_user.full_name

    logger.info(f"'next_word' callback from {full_name} ({username})")
    
    # Advance to next word
    user_word_state = await UserWordState.from_state(state)
    
    if user_word_state.is_valid():
        # Проверяем, было ли слово показано
        word_shown = user_word_state.get_flag('word_shown', False)
        
        # ИСПРАВЛЕНО: Если слово еще не было показано - показываем полную информацию о нем
        if not word_shown and user_word_state.word_data:
            current_word = user_word_state.word_data
            
            # Получаем информацию о слове
            word_foreign = current_word.get("word_foreign", "N/A")
            transcription = current_word.get("transcription", "")
            translation = current_word.get("translation", "")
            
            # Формируем сообщение с информацией о пропущенном слове
            message_text = f"📖 Вот это слово:\n\n"
            message_text += f"Перевод: <b>{translation}</b>\n\n"
            message_text += f"Слово: <code>{word_foreign}</code>\n"
            
            if transcription:
                message_text += f"Транскрипция: <b>[{transcription}]</b>\n\n"
            else:
                message_text += "\n"
            
            message_text += "🔄 Переходим к следующему слову..."
            
            await callback.message.answer(
                message_text,
                parse_mode="HTML"
            )
        else:
            # Если слово было показано - обычное сообщение
            await callback.message.answer("🔄 Переходим к следующему слову...")
        
        # Reset word_shown flag
        user_word_state.set_flag('word_shown', False)
        
        # НОВОЕ: Отмечаем слово как обработанное
        user_word_state.mark_word_as_processed()
        
        # Advance to next word
        success = user_word_state.advance_to_next_word()
        
        if not success:
            # НОВОЕ: Пытаемся загрузить следующую партию
            api_client = get_api_client_from_bot(callback.bot)
            next_batch_loaded = await load_next_batch(callback.message, state, user_word_state, api_client)
            
            if next_batch_loaded:
                # Партия загружена - показываем первое слово из новой партии
                await state.set_state(StudyStates.studying)
                await show_study_word(callback.message, state, need_new_message=True)
                await callback.answer()
                return
            else:
                # Действительно закончились все слова
                await state.set_state(StudyStates.study_completed)
                
                # Показываем финальную статистику
                session_stats = user_word_state.get_session_statistics()
                
                await callback.message.answer(
                    f"🎉 <b>Поздравляем! Вы действительно изучили ВСЕ доступные слова!</b>\n\n"
                    f"📊 <b>Статистика сессии:</b>\n"
                    f"📚 Всего слов изучено: {session_stats['total_words_processed']}\n"
                    f"📦 Загружено партий: {session_stats['batches_loaded']}\n"
                    f"📈 Среднее слов в партии: {session_stats['average_words_per_batch']:.0f}\n\n"
                    f"🏆 Это отличный результат!\n\n"
                    f"📊 Чтобы посмотреть общую статистику, используйте команду /stats\n"
                    f"⚙️ Чтобы изменить настройки, используйте /settings\n"
                    f"🔄 Чтобы начать изучение заново, используйте /study",
                    parse_mode="HTML"
                )
                return
        
        # Save updated state
        await user_word_state.save_to_state(state)
        
        # НОВОЕ: Возвращаемся в основное состояние изучения
        await state.set_state(StudyStates.studying)
        
        # Show next word
        await show_study_word(callback.message, state, need_new_message=True)
    else:
        # Fallback to old approach if state model is invalid
        logger.warning("UserWordState invalid, using fallback approach to advance to next word")
        
        # Get current state data
        user_data = await state.get_data()
        current_index = user_data.get("current_study_index", 0) + 1
        
        study_words = user_data.get("study_words", [])
        
        if current_index >= len(study_words):
            # НОВОЕ: В fallback режиме тоже переходим в состояние завершения
            await state.set_state(StudyStates.study_completed)
            await callback.message.answer(
                "🎉 Партия слов завершена!\n\n"
                "📊 Чтобы посмотреть статистику, используйте команду /stats\n"
                "⚙️ Чтобы изменить настройки и продолжить изучение, используйте /settings\n"
                "🔄 Чтобы начать изучение заново, используйте /study"
            )
            return
        
        # Update state with new index
        await state.update_data(current_study_index=current_index)
        
        # ИСПРАВЛЕНО: Промежуточное сообщение для fallback случая
        await callback.message.answer("🔄 Переходим к следующему слову...")
        
        # НОВОЕ: Возвращаемся в основное состояние изучения
        await state.set_state(StudyStates.studying)
        
        # Show next word
        await show_study_word(callback.message, state, need_new_message=True)
    
    await callback.answer()


@navigation_router.callback_query(F.data == "confirm_next_word", StudyStates.confirming_word_knowledge)
async def process_confirm_next_word(callback: CallbackQuery, state: FSMContext):
    """
    Process confirmation to go to the next word.
    ИЗМЕНЕНО: Убрали обновление оценки - оно уже произошло в word_know.
    ОБНОВЛЕНО: Поддержка автоматической загрузки следующих партий.
    
    Args:
        callback: The callback query from Telegram
        state: The FSM state context
    """
    user_id = callback.from_user.id
    username = callback.from_user.username
    full_name = callback.from_user.full_name

    logger.info(f"'confirm_next_word' callback from {full_name} ({username})")
    
    # Получаем состояние слова
    user_word_state = await UserWordState.from_state(state)
    
    # УБРАНО: Обновление оценки слова - оно уже произошло в word_know
    # Просто переходим к следующему слову
    
    if user_word_state.is_valid():
        # Проверяем, было ли слово показано (всегда должно быть True после word_know)
        word_shown = user_word_state.get_flag('word_shown', False)
        
        # ИСПРАВЛЕНО: Если слово не было показано после word_know - показываем полную информацию
        if not word_shown and user_word_state.word_data:
            current_word = user_word_state.word_data
            
            # Получаем информацию о слове
            word_foreign = current_word.get("word_foreign", "N/A")
            transcription = current_word.get("transcription", "")
            translation = current_word.get("translation", "")
            
            # Получаем обновленные данные пользователя
            user_word_data = current_word.get("user_word_data", {})
            new_check_interval = user_word_data.get("check_interval", 0)
            new_next_check_date = user_word_data.get("next_check_date")
            
            # Получаем настройки для отображения отладочной информации
            settings = await get_user_language_settings(callback, state)
            show_debug = settings.get("show_debug", False)
            
            # Формируем сообщение с полной информацией о изученном слове
            message_text = f"✅ Слово изучено успешно:\n\n"
            message_text += f"Перевод: <b>{translation}</b>\n\n"
            message_text += f"Слово: <code>{word_foreign}</code>\n"
            
            if transcription:
                message_text += f"Транскрипция: <b>[{transcription}]</b>\n\n"
            else:
                message_text += "\n"
            
            # Показываем информацию об интервалах
            if show_debug:
                message_text += f"✅ Оценка: 1 (знаю слово)\n"
                message_text += f"⏱ Интервал повторения: {new_check_interval} (дней)\n"
                if new_next_check_date:
                    formatted_date = format_date(new_next_check_date)
                    message_text += f"🔄 Следующее повторение: {formatted_date}\n\n"
                else:
                    message_text += "🔄 Дата повторения обновлена\n\n"
            else:
                # Для обычных пользователей показываем упрощенную информацию
                if new_next_check_date:
                    formatted_date = format_date(new_next_check_date)
                    message_text += f"📅 Следующее повторение: {formatted_date}\n\n"
            
            message_text += "🔄 Переходим к следующему слову..."
            
            await callback.message.answer(
                message_text,
                parse_mode="HTML"
            )
        else:
            # Слово было показано (обычный случай)
            await callback.message.answer("🔄 Переходим к следующему слову...")
        
        # Reset word_shown flag
        user_word_state.set_flag('word_shown', False)
        
        # Remove pending flags
        user_word_state.remove_flag('pending_next_word')
        user_word_state.remove_flag('pending_word_know')
        
        # НОВОЕ: Отмечаем слово как обработанное
        user_word_state.mark_word_as_processed()
        
        # Advance to next word
        success = user_word_state.advance_to_next_word()
        
        if not success:
            # НОВОЕ: Пытаемся загрузить следующую партию
            api_client = get_api_client_from_bot(callback.bot)
            next_batch_loaded = await load_next_batch(callback.message, state, user_word_state, api_client)
            
            if next_batch_loaded:
                # Партия загружена - показываем первое слово из новой партии
                await state.set_state(StudyStates.studying)
                await show_study_word(callback.message, state, need_new_message=True)
                await callback.answer()
                return
            else:
                # Действительно закончились все слова
                await state.set_state(StudyStates.study_completed)
                
                # Показываем финальную статистику
                session_stats = user_word_state.get_session_statistics()
                
                await callback.message.answer(
                    f"🎉 <b>Поздравляем! Вы действительно изучили ВСЕ доступные слова!</b>\n\n"
                    f"📊 <b>Статистика сессии:</b>\n"
                    f"📚 Всего слов изучено: {session_stats['total_words_processed']}\n"
                    f"📦 Загружено партий: {session_stats['batches_loaded']}\n"
                    f"📈 Среднее слов в партии: {session_stats['average_words_per_batch']:.0f}\n\n"
                    f"🏆 Это отличный результат!\n\n"
                    f"📊 Чтобы посмотреть общую статистику, используйте команду /stats\n"
                    f"⚙️ Чтобы изменить настройки, используйте /settings\n"
                    f"🔄 Чтобы начать изучение заново, используйте /study",
                    parse_mode="HTML"
                )
                return
        
        # Save updated state
        await user_word_state.save_to_state(state)
        
        # НОВОЕ: Возвращаемся в основное состояние изучения
        await state.set_state(StudyStates.studying)
        
        # Show next word
        await show_study_word(callback.message, state, need_new_message=True)
    else:
        # Fallback to old approach if state model is invalid
        logger.warning("UserWordState invalid, using fallback approach to advance to next word")
        
        # Get current state data
        user_data = await state.get_data()
        current_index = user_data.get("current_study_index", 0) + 1
        
        study_words = user_data.get("study_words", [])
        
        if current_index >= len(study_words):
            # НОВОЕ: В fallback режиме тоже переходим в состояние завершения
            await state.set_state(StudyStates.study_completed)
            await callback.message.answer(
                "🎉 Партия слов завершена!\n\n"
                "📊 Чтобы посмотреть статистику, используйте команду /stats\n"
                "⚙️ Чтобы изменить настройки и продолжить изучение, используйте /settings\n"
                "🔄 Чтобы начать изучение заново, используйте /study"
            )
            return
        
        # Update state with new index
        await state.update_data(current_study_index=current_index)
        
        # ИСПРАВЛЕНО: Промежуточное сообщение для fallback случая
        await callback.message.answer("🔄 Переходим к следующему слову...")
        
        # НОВОЕ: Возвращаемся в основное состояние изучения
        await state.set_state(StudyStates.studying)
        
        # Show next word
        await show_study_word(callback.message, state, need_new_message=True)
    
    await callback.answer()
    