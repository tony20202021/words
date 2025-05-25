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
from app.bot.handlers.study.study_words import show_study_word
from app.bot.keyboards.study_keyboards import create_word_keyboard
from app.utils.formatting_utils import format_date, format_study_word_message, format_used_hints
from app.utils.settings_utils import get_user_language_settings

# Импортируем централизованные состояния
from app.bot.states.centralized_states import StudyStates

# Создаем роутер для обработчиков действий со словами
word_router = Router()

logger = setup_logger(__name__)

@word_router.callback_query(F.data == "show_word", StudyStates.studying)
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

@word_router.callback_query(F.data == "next_word", StudyStates.viewing_word_details)        
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
        
        # Advance to next word
        success = user_word_state.advance_to_next_word()
        
        if not success:
            # НОВОЕ: Переходим в состояние завершения изучения
            await state.set_state(StudyStates.study_completed)
            await callback.message.answer(
                "🎉 Поздравляем! Вы изучили все доступные слова!\n\n"
                "📊 Чтобы посмотреть статистику, используйте команду /stats\n"
                "⚙️ Чтобы изменить настройки и продолжить изучение, используйте /settings\n"
                "🔄 Чтобы начать изучение заново, используйте /study"
            )
            return
        
        # Save updated state
        await user_word_state.save_to_state(state)
        
        # НОВОЕ: Возвращаемся в основное состояние изучения
        await state.set_state(StudyStates.studying)
        
        # Show next word
        await show_study_word(callback.message, state)
    else:
        # Fallback to old approach if state model is invalid
        logger.warning("UserWordState invalid, using fallback approach to advance to next word")
        
        # Get current state data
        user_data = await state.get_data()
        current_index = user_data.get("current_study_index", 0) + 1
        
        study_words = user_data.get("study_words", [])
        
        if current_index >= len(study_words):
            # НОВОЕ: Переходим в состояние завершения изучения
            await state.set_state(StudyStates.study_completed)
            await callback.message.answer(
                "🎉 Поздравляем! Вы изучили все доступные слова!\n\n"
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
        await show_study_word(callback.message, state)
    
    await callback.answer()

@word_router.callback_query(F.data == "show_word", StudyStates.confirming_word_knowledge)
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

@word_router.callback_query(F.data == "toggle_word_skip", StudyStates.studying)
@word_router.callback_query(F.data == "toggle_word_skip", StudyStates.viewing_word_details)
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

@word_router.callback_query(F.data == "word_know", StudyStates.studying)
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

@word_router.callback_query(F.data == "confirm_next_word", StudyStates.confirming_word_knowledge)
async def process_confirm_next_word(callback: CallbackQuery, state: FSMContext):
    """
    Process confirmation to go to the next word.
    ИЗМЕНЕНО: Убрали обновление оценки - оно уже произошло в word_know.
    
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
        
        # Advance to next word
        success = user_word_state.advance_to_next_word()
        
        if not success:
            # НОВОЕ: Переходим в состояние завершения изучения
            await state.set_state(StudyStates.study_completed)
            await callback.message.answer(
                "🎉 Поздравляем! Вы изучили все доступные слова!\n\n"
                "📊 Чтобы посмотреть статистику, используйте команду /stats\n"
                "⚙️ Чтобы изменить настройки и продолжить изучение, используйте /settings\n"
                "🔄 Чтобы начать изучение заново, используйте /study"
            )
            return
        
        # Save updated state
        await user_word_state.save_to_state(state)
        
        # НОВОЕ: Возвращаемся в основное состояние изучения
        await state.set_state(StudyStates.studying)
        
        # Show next word
        await show_study_word(callback.message, state)
    else:
        # Fallback to old approach if state model is invalid
        logger.warning("UserWordState invalid, using fallback approach to advance to next word")
        
        # Get current state data
        user_data = await state.get_data()
        current_index = user_data.get("current_study_index", 0) + 1
        
        study_words = user_data.get("study_words", [])
        
        if current_index >= len(study_words):
            # НОВОЕ: Переходим в состояние завершения изучения
            await state.set_state(StudyStates.study_completed)
            await callback.message.answer(
                "🎉 Поздравляем! Вы изучили все доступные слова!\n\n"
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
        await show_study_word(callback.message, state)
    
    await callback.answer()

@word_router.callback_query(F.data == "word_dont_know", StudyStates.studying)
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
    