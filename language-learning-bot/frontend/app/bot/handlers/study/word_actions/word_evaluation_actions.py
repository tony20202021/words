"""
Handlers for word evaluation actions during the study process.
Обработчики для оценки слов в процессе изучения (знаю/не знаю).
ОБНОВЛЕНО: Добавлена поддержка автоматической загрузки следующих партий.
"""

from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.utils.api_utils import get_api_client_from_bot
from app.utils.logger import setup_logger
from app.utils.error_utils import validate_state_data
from app.utils.state_models import UserWordState
from app.utils.word_data_utils import update_word_score
from app.utils.formatting_utils import format_date
from app.utils.settings_utils import get_user_language_settings

# Импортируем централизованные состояния
from app.bot.states.centralized_states import StudyStates

# Создаем роутер для обработчиков оценки слов
evaluation_router = Router()

logger = setup_logger(__name__)


@evaluation_router.callback_query(F.data == "word_know", StudyStates.studying)
async def process_word_know(callback: CallbackQuery, state: FSMContext):
    """
    Process callback when user knows the word.
    ИЗМЕНЕНО: Сразу обновляем оценку на 1 здесь.
    
    Args:
        callback: The callback query from Telegram
        state: The FSM state context
    """
    user_id = callback.from_user.id
    username = callback.from_user.username
    full_name = callback.from_user.full_name

    logger.info(f"'word_know' callback from {full_name} ({username})")
    
    # Validate state data
    is_valid, state_data = await validate_state_data(
        state, 
        ["current_word", "current_word_id", "db_user_id"],
        callback,
        "Ошибка: недостаточно данных для оценки слова"
    )
    
    if not is_valid:
        logger.error(f"not is_valid")
        return
    
    # Get required data
    current_word = state_data["current_word"]
    current_word_id = state_data["current_word_id"]
    db_user_id = state_data["db_user_id"]
    
    # Проверим, включена ли отладочная информация
    settings = await get_user_language_settings(callback, state)
    show_debug = settings.get("show_debug", False)
    
    try:
        # ПЕРЕНЕСЕНО СЮДА: Обновляем word score на 1 сразу
        success, result = await update_word_score(
            callback.bot,
            db_user_id,
            current_word_id,
            score=1,  # Устанавливаем оценку 1 сразу
            word=current_word,
            message_obj=callback
        )
        
        if not success:
            logger.error(f"Failed to update word score")
            await callback.answer("Ошибка при обновлении оценки слова")
            return
        
        # Обновляем данные слова в состоянии
        if 'user_word_data' not in current_word:
            current_word['user_word_data'] = {}
        current_word['user_word_data'].update(result)
        
        # Show word information
        word_foreign = current_word.get("word_foreign")
        transcription = current_word.get("transcription", "")
        
        # ИЗМЕНЕНО: Получаем НОВЫЕ данные из результата обновления
        new_check_interval = result.get("check_interval", 0)
        new_next_check_date = result.get("next_check_date")
        
        # Формируем сообщение с ОБНОВЛЕННОЙ информацией
        message_text = f"✅ Отлично! Вы знаете это слово.\n\n"
        message_text += f"Слово: <code>{word_foreign}</code>\n\n"
        message_text += f"Транскрипция: <b>[{transcription}]</b>\n\n"
        
        # Показываем обновленную информацию об интервалах
        if show_debug:
            message_text += f"✅ Оценка обновлена на 1\n"
            message_text += f"⏱ Новый интервал: {new_check_interval} (дней)\n"
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
        
        # Создаем клавиатуру с двумя кнопками
        keyboard = InlineKeyboardBuilder()
        keyboard.button(
            text="✅ К следующему слову",
            callback_data="confirm_next_word"
        )
        keyboard.button(
            text="❌ Ой, все-таки не знаю",
            callback_data="show_word"  
            # Внутри show_word уже есть обновление оценки на 0, поэтому ничего дополнительного не нужно
        )
        keyboard.adjust(1)  # Размещаем кнопки одну под другой
        
        # НОВОЕ: Переходим в состояние подтверждения знания слова
        await state.set_state(StudyStates.confirming_word_knowledge)
        
        await callback.message.answer(
            message_text,
            parse_mode="HTML",
            reply_markup=keyboard.as_markup()
        )
        
        # Сохраняем флаг, что нужно перейти к следующему слову при подтверждении
        user_word_state = await UserWordState.from_state(state)
        if user_word_state.is_valid():
            user_word_state.set_flag('pending_next_word', True)
            user_word_state.set_flag('pending_word_know', True)  # Флаг для обработки в show_word
            # Обновляем данные слова в состоянии
            user_word_state.word_data = current_word
            await user_word_state.save_to_state(state)
        
    except Exception as e:
        logger.error(f"Error processing word_know: {e}", exc_info=True)
        await callback.message.answer(
            f"❌ Ошибка при обработке слова: {str(e)}"
        )
    
    await callback.answer()


@evaluation_router.callback_query(F.data == "word_dont_know", StudyStates.studying)
async def process_word_dont_know(callback: CallbackQuery, state: FSMContext):
    """
    Process callback when user doesn't know the word.
    
    Args:
        callback: The callback query from Telegram
        state: The FSM state context
    """
    user_id = callback.from_user.id
    username = callback.from_user.username
    full_name = callback.from_user.full_name

    logger.info(f"'word_dont_know' callback from {full_name} ({username})")
    
    # Validate state data
    is_valid, state_data = await validate_state_data(
        state, 
        ["current_word", "current_word_id", "db_user_id"],
        callback,
        "Ошибка: недостаточно данных для оценки слова"
    )
    
    if not is_valid:
        logger.error(f"not is_valid")
        return
    
    # Get required data
    current_word = state_data["current_word"]
    current_word_id = state_data["current_word_id"]
    db_user_id = state_data["db_user_id"]
    
    # Проверим, включена ли отладочная информация
    settings = await get_user_language_settings(callback, state)
    show_debug = settings.get("show_debug", False)
    
    try:
        # Update word score to 0 (not known)
        success, result = await update_word_score(
            callback.bot,
            db_user_id,
            current_word_id,
            score=0,  # Устанавливаем оценку 0
            word=current_word,
            message_obj=callback
        )
        
        if not success:
            logger.error(f"Failed to update word score")
            await callback.answer("Ошибка при обновлении оценки слова")
            return
        
        # Обновляем данные слова в состоянии
        if 'user_word_data' not in current_word:
            current_word['user_word_data'] = {}
        current_word['user_word_data'].update(result)
        
        # Show word information
        word_foreign = current_word.get("word_foreign")
        transcription = current_word.get("transcription", "")
        translation = current_word.get("translation", "")
        
        # ИЗМЕНЕНО: Получаем НОВЫЕ данные из результата обновления
        new_check_interval = result.get("check_interval", 0)
        new_next_check_date = result.get("next_check_date")
        
        # Формируем сообщение с ОБНОВЛЕННОЙ информацией
        message_text = f"📚 Не страшно! Изучаем это слово.\n\n"
        message_text += f"Перевод: <b>{translation}</b>\n\n"
        message_text += f"Слово: <code>{word_foreign}</code>\n\n"
        message_text += f"Транскрипция: <b>[{transcription}]</b>\n\n"
        
        # Показываем обновленную информацию об интервалах
        if show_debug:
            message_text += f"📝 Оценка установлена на 0\n"
            message_text += f"⏱ Интервал: {new_check_interval} (дней)\n"
            if new_next_check_date:
                formatted_date = format_date(new_next_check_date)
                message_text += f"🔄 Следующее повторение: {formatted_date}\n\n"
            else:
                message_text += "🔄 Дата повторения обновлена\n\n"
        else:
            # Для обычных пользователей показываем упрощенную информацию
            message_text += f"💡 Это слово будет показано снова при следующем изучении.\n\n"
        
        # Создаем клавиатуру с кнопкой перехода к следующему слову
        keyboard = InlineKeyboardBuilder()
        keyboard.button(
            text="➡️ К следующему слову",
            callback_data="confirm_next_word"
        )
        
        # НОВОЕ: Переходим в состояние подтверждения знания слова
        await state.set_state(StudyStates.confirming_word_knowledge)
        
        await callback.message.answer(
            message_text,
            parse_mode="HTML",
            reply_markup=keyboard.as_markup()
        )
        
        # Сохраняем флаг, что нужно перейти к следующему слову при подтверждении
        user_word_state = await UserWordState.from_state(state)
        if user_word_state.is_valid():
            user_word_state.set_flag('pending_next_word', True)
            user_word_state.set_flag('word_shown', True)  # Помечаем слово как показанное
            # Обновляем данные слова в состоянии
            user_word_state.word_data = current_word
            await user_word_state.save_to_state(state)
        
    except Exception as e:
        logger.error(f"Error processing word_dont_know: {e}", exc_info=True)
        await callback.message.answer(
            f"❌ Ошибка при обработке слова: {str(e)}"
        )
    
    await callback.answer()
    