"""
Handlers for word actions during the study process.
"""

from datetime import timedelta

from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from app.utils.api_utils import get_api_client_from_bot
from app.utils.logger import setup_logger
from app.utils.error_utils import validate_state_data
from app.utils.state_models import UserWordState
from app.utils.word_data_utils import update_word_score
from app.utils.formatting_utils import format_date
from app.utils.formatting_utils import format_study_word_message
from app.bot.handlers.study.study_words import show_study_word
from app.bot.keyboards.study_keyboards import create_word_keyboard
from app.utils.formatting_utils import format_date, format_study_word_message, format_active_hints
from app.utils.settings_utils import get_user_language_settings


# Создаем роутер для обработчиков действий со словами
word_router = Router()

logger = setup_logger(__name__)

@word_router.callback_query(F.data == "show_word")
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

    logger.info(f"'show_word' callback from {full_name} ({username})")
    
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
        is_skipped=current_skipped # оставляем старое значени
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
    
    # Get active hints
    active_hints = user_word_state.get_active_hints()
    
    # Get used hints
    used_hints = user_word_state.get_flag("used_hints", [])
    
    # Get show_hints setting
    from app.utils.settings_utils import get_show_hints_setting
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
    hint_text = await format_active_hints(
        bot=callback.bot,
        user_id=user_word_state.user_id,
        word_id=user_word_state.word_id,
        current_word=current_word,
        active_hints=active_hints,
        include_header=True
    )
    
    updated_message += hint_text
    
    # Create updated keyboard 
    keyboard = create_word_keyboard(
        current_word, 
        word_shown=True, 
        show_hints=show_hints,
        active_hints=active_hints,
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
        
@word_router.callback_query(F.data == "next_word")
async def process_next_word(callback: CallbackQuery, state: FSMContext):
    """
    Process callback to go to the next word without changing score.
    
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
        # Reset word_shown flag
        user_word_state.set_flag('word_shown', False)
        
        # Advance to next word
        user_word_state.advance_to_next_word()
        
        # Save updated state
        await user_word_state.save_to_state(state)
        
        # Отправляем промежуточное сообщение
        await callback.message.answer("🔄 Переходим к следующему слову...")
        
        # Show next word (используем callback.message вместо callback)
        await show_study_word(callback.message, state)
    else:
        # Fallback to old approach if state model is invalid
        logger.warning("UserWordState invalid, using fallback approach to advance to next word")
        
        # Get current state data
        user_data = await state.get_data()
        current_index = user_data.get("current_study_index", 0) + 1
        
        # Update state with new index
        await state.update_data(current_study_index=current_index)
        
        # Отправляем промежуточное сообщение
        await callback.message.answer("🔄 Переходим к следующему слову...")
        
        # Show next word (используем callback.message вместо callback)
        await show_study_word(callback.message, state)
    
    await callback.answer()

@word_router.callback_query(F.data == "toggle_word_skip")
async def process_toggle_word_skip(callback: CallbackQuery, state: FSMContext):
    """
    Process callback when user wants to toggle the skip flag for the word.
    
    Args:
        callback: The callback query from Telegram
        state: The FSM state context
    """
    user_id = callback.from_user.id
    username = callback.from_user.username
    full_name = callback.from_user.full_name

    logger.info(f"'toggle_word_skip' callback from {full_name} ({username})")
    
    # Validate state data
    is_valid, state_data = await validate_state_data(
        state, 
        ["current_word", "current_word_id", "db_user_id"],
        callback,
        "Ошибка: недостаточно данных для изменения флага пропуска слова"
    )
    
    if not is_valid:
        return
    
    # Get required data
    current_word = state_data["current_word"]
    current_word_id = state_data["current_word_id"]
    db_user_id = state_data["db_user_id"]
    
    # Получаем настройку отображения отладочной информации
    settings = await get_user_language_settings(callback, state)
    show_debug = settings.get("show_debug", False)
    
    # Проверяем текущее состояние флага пропуска
    user_word_data = current_word.get("user_word_data", {})
    current_skip_status = user_word_data.get("is_skipped", False)
    
    # Инвертируем статус пропуска
    new_skip_status = not current_skip_status
    
    try:
        # Update word with new skip status
        success, result = await update_word_score(
            callback.bot,
            db_user_id,
            current_word_id,
            score=0,
            word=current_word,
            message_obj=callback,
            is_skipped=new_skip_status  # Новый статус пропуска
        )
        
        if not success:
            return
        
        # Show word information
        word_foreign = current_word.get("word_foreign")
        transcription = current_word.get("transcription", "")
        
        # Формируем сообщение о смене статуса
        status_message = (
            f"⏩ Статус изменен: слово теперь будет {'пропускаться' if new_skip_status else 'показываться'} в будущем.\n\n"
            f"Слово: <b>{word_foreign}</b>\n"
        )
        
        if transcription:
            status_message += f"Транскрипция: <b>[{transcription}]</b>\n\n"
        
        # Добавляем отладочную информацию, если она включена
        if show_debug:
            status_message += f"🔍 <b>Отладочная информация:</b>\n"
            status_message += f"ID слова: {current_word_id}\n"
            status_message += f"Предыдущий статус пропуска: {current_skip_status}\n"
            status_message += f"Новый статус пропуска: {new_skip_status}\n\n"
        
        await callback.message.answer(
            status_message,
            parse_mode="HTML"
        )
        
        # Обновляем слово в состоянии
        user_word_state = await UserWordState.from_state(state)
        
        if user_word_state.is_valid() and user_word_state.word_data:
            # Обновляем данные о пропуске в локальном состоянии
            if "user_word_data" not in user_word_state.word_data:
                user_word_state.word_data["user_word_data"] = {}
                
            user_word_state.word_data["user_word_data"]["is_skipped"] = new_skip_status
            
            # Логирование данных для отладки
            logger.info(f"Updated word data with new skip status: {new_skip_status}")
            logger.info(f"Word data is_skipped: {user_word_state.word_data.get('user_word_data', {}).get('is_skipped')}")
            
            # Сохраняем обновленное состояние
            await user_word_state.save_to_state(state)
            
            # Get show_hints setting
            from app.utils.settings_utils import get_show_hints_setting
            show_hints = await get_show_hints_setting(callback, state)
            
            # Получаем список использованных подсказок
            used_hints = user_word_state.get_flag("used_hints", [])
            
            # Показываем слово снова с обновленной клавиатурой и флагом пропуска
            await show_study_word(callback.message, state)
            
    except Exception as e:
        logger.error(f"Error processing toggle_word_skip: {e}", exc_info=True)
        await callback.message.answer(
            f"❌ Ошибка при обработке флага пропуска слова: {str(e)}"
        )
    
    await callback.answer()

@word_router.callback_query(F.data == "word_know")
async def process_word_know(callback: CallbackQuery, state: FSMContext):
    """
    Process callback when user knows the word.
    
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
        # Важно: УДАЛЯЕМ обновление score тут
        # Теперь score будет обновляться только при подтверждении в confirm_next_word
        
        # Show word information
        word_foreign = current_word.get("word_foreign")
        transcription = current_word.get("transcription", "")
        
        # Получаем информацию о слове из текущего состояния
        user_word_data = current_word.get("user_word_data", {})
        check_interval = user_word_data.get("check_interval", 0)
        next_check_date = user_word_data.get("next_check_date")
        
        # Формируем сообщение, учитывая настройку отладочной информации
        message_text = f"✅ Отлично! Вы знаете это слово.\n\n"
        message_text += f"Слово: <code>{word_foreign}</code>\n\n"
        message_text += f"Транскрипция: <b>[{transcription}]</b>\n\n"
        
        # Добавляем информацию об интервалах только если включен отладочный режим
        if show_debug:
            message_text += f"⏱ Текущий интервал: {check_interval} (дней)\n"
            if next_check_date:
                formatted_date = format_date(next_check_date)
                message_text += f"🔄 Текущее запланированное повторение: {formatted_date}\n\n"
            else:
                message_text += "🔄 Дата повторения пока не задана\n\n"
            
            message_text += "ℹ️ После подтверждения интервал будет увеличен\n\n"
        
        message_text += "Подтвердите знание слова или вернитесь к изучению."
        
        # Создаем клавиатуру с двумя кнопками
        keyboard = InlineKeyboardBuilder()
        keyboard.button(
            text="✅ К следующему слову",
            callback_data="confirm_next_word"
        )
        keyboard.button(
            text="❌ Ой, все-таки не знаю",
            callback_data="show_word"
        )
        keyboard.adjust(1)  # Размещаем кнопки одну под другой
        
        await callback.message.answer(
            message_text,
            parse_mode="HTML",
            reply_markup=keyboard.as_markup()
        )
        
        # Сохраняем флаг, что нужно перейти к следующему слову при подтверждении
        user_word_state = await UserWordState.from_state(state)
        if user_word_state.is_valid():
            user_word_state.set_flag('pending_next_word', True)
            user_word_state.set_flag('pending_word_know', True)  # Новый флаг для подтверждения знания
            await user_word_state.save_to_state(state)
        
    except Exception as e:
        logger.error(f"Error processing word_know: {e}", exc_info=True)
        await callback.message.answer(
            f"❌ Ошибка при обработке слова: {str(e)}"
        )
    
    await callback.answer()

@word_router.callback_query(F.data == "confirm_next_word")
async def process_confirm_next_word(callback: CallbackQuery, state: FSMContext):
    """
    Process confirmation to go to the next word.
    
    Args:
        callback: The callback query from Telegram
        state: The FSM state context
    """
    user_id = callback.from_user.id
    username = callback.from_user.username
    full_name = callback.from_user.full_name

    logger.info(f"'confirm_next_word' callback from {full_name} ({username})")
    
    # Get required data
    state_data = await state.get_data()
    current_word = state_data.get("current_word")
    current_word_id = state_data.get("current_word_id")
    db_user_id = state_data.get("db_user_id")
    
    # Получаем настройку отображения отладочной информации
    settings = await get_user_language_settings(callback, state)
    show_debug = settings.get("show_debug", False)
    
    # Получаем состояние слова
    user_word_state = await UserWordState.from_state(state)
    
    # Проверяем, нужно ли обновить оценку слова
    if user_word_state.is_valid() and user_word_state.get_flag('pending_word_know', False):
        # Обновляем word score на 1 только при подтверждении
        success, result = await update_word_score(
            callback.bot,
            db_user_id,
            current_word_id,
            score=1,  # Теперь устанавливаем оценку 1 здесь
            word=current_word,
            message_obj=callback
        )
        
        if not success:
            logger.error(f"Failed to update word score")
            await callback.answer("Ошибка при обновлении оценки слова")
            return
            
        # Отправляем сообщение об успешном обновлении, если включен режим отладки
        if show_debug:
            debug_info = (
                f"✅ Оценка слова обновлена успешно:\n"
                f"Новая оценка: 1\n"
                f"Новый интервал: {result.get('check_interval', 0)} дней\n"
                f"Дата следующей проверки: {format_date(result.get('next_check_date', ''))}\n"
            )
            await callback.message.answer(debug_info)
            
        # Сбрасываем флаг ожидания обновления оценки
        user_word_state.remove_flag('pending_word_know')
        
    if user_word_state.is_valid():
        # Reset word_shown flag
        user_word_state.set_flag('word_shown', False)
        
        # Remove pending flag
        user_word_state.remove_flag('pending_next_word')
        
        # Advance to next word
        user_word_state.advance_to_next_word()
        
        # Save updated state
        await user_word_state.save_to_state(state)
        
        # Отправляем новое сообщение с следующим словом
        await callback.message.answer("🔄 Переходим к следующему слову...")
        
        # Show next word (заменяем callback на callback.message)
        await show_study_word(callback.message, state)
    else:
        # Fallback to old approach if state model is invalid
        logger.warning("UserWordState invalid, using fallback approach to advance to next word")
        
        # Get current state data
        user_data = await state.get_data()
        current_index = user_data.get("current_study_index", 0) + 1
        
        # Update state with new index
        await state.update_data(current_study_index=current_index)
        
        # Отправляем новое сообщение с следующим словом
        await callback.message.answer("🔄 Переходим к следующему слову...")
        
        # Show next word (заменяем callback на callback.message)
        await show_study_word(callback.message, state)
    
    await callback.answer()
    