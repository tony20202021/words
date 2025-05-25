"""
Refactored handlers for hint toggling.
Now uses centralized utilities and constants.
"""

from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext

from app.utils.api_utils import get_api_client_from_bot
from app.utils.logger import setup_logger
from app.utils.error_utils import validate_state_data
from app.utils.state_models import UserWordState
from app.utils.word_data_utils import get_hint_text, update_word_score
from app.utils.hint_constants import get_hint_key, get_hint_name, get_hint_icon
from app.bot.keyboards.study_keyboards import create_word_keyboard
from app.utils.formatting_utils import format_study_word_message, format_used_hints
from app.utils.settings_utils import get_show_hints_setting

# Import callback utilities
from app.utils.callback_constants import CallbackParser

# Импортируем централизованные состояния
from app.bot.states.centralized_states import StudyStates, HintStates

# Создаем вложенный роутер для обработчиков переключения подсказок
toggle_router = Router()

# Set up logging
logger = setup_logger(__name__)


@toggle_router.callback_query(F.data.startswith("hint_toggle_"), StudyStates.studying)
@toggle_router.callback_query(F.data.startswith("hint_toggle_"), StudyStates.viewing_word_details)
async def process_hint_toggle(callback: CallbackQuery, state: FSMContext):
    """
    Process callback when user wants to toggle a hint visibility.
    Updates the current message to show or hide the hint.
    Now uses improved callback parsing and FSM states.
    
    Args:
        callback: The callback query from Telegram
        state: The FSM state context
    """
    logger.info(f"Received hint toggle callback: {callback.data}")
    
    # Parse callback data using the new parser
    parsed = CallbackParser.parse_hint_action(callback.data)
    if not parsed:
        logger.error(f"Could not parse callback_data: {callback.data}")
        await callback.answer("Ошибка формата данных")
        return
    
    action, hint_type, word_id = parsed
    logger.info(f"Parsed toggle callback: hint_type={hint_type}, word_id={word_id}")
    
    # Validate state data
    is_valid, state_data = await validate_state_data(
        state, 
        ["current_word", "db_user_id"],
        callback,
        "Ошибка: недостаточно данных для отображения подсказки"
    )
    
    if not is_valid:
        return
    
    # Get current word and user ID
    current_word = state_data["current_word"]
    db_user_id = state_data["db_user_id"]
    
    # Verify word ID matches current word
    current_word_id = None
    for id_field in ["id", "_id", "word_id"]:
        if id_field in current_word and current_word[id_field]:
            current_word_id = str(current_word[id_field])
            if current_word_id == word_id:
                break
    
    if not current_word_id or current_word_id != word_id:
        logger.error(f"Word ID mismatch: callback_word_id={word_id}, current_word_id={current_word_id}")
        await callback.answer("Ошибка: несоответствие ID слова")
        return
    
    # Get hint key and name
    hint_key = get_hint_key(hint_type)
    hint_name = get_hint_name(hint_type)
    hint_icon = get_hint_icon(hint_type)
    
    if not hint_key or not hint_name:
        await callback.answer("Ошибка: неизвестный тип подсказки")
        return
    
    # Get hint text
    hint_text = await get_hint_text(
        callback.bot, 
        db_user_id, 
        word_id, 
        hint_key, 
        current_word
    )
    
    if not hint_text:
        logger.error("Hint text not found")
        await callback.answer("Подсказка не найдена")
        return
    
    # Get current user word state
    user_word_state = await UserWordState.from_state(state)
    
    # Get list of used hints
    used_hints = user_word_state.get_flag("used_hints", []) if user_word_state.is_valid() else []
    
    # Toggle hint state - add hint to used hints and set score to 0
    if hint_type not in used_hints:
        used_hints.append(hint_type)
        
        # Update user word state
        user_word_state.set_flag("used_hints", used_hints)
        
        # Set score to 0 for using hint
        await update_word_score(
            callback.bot,
            db_user_id,
            word_id,
            score=0,
            word=current_word,
            message_obj=callback
        )
        
        # НОВОЕ: Переходим в состояние просмотра подсказки
        await state.set_state(HintStates.viewing)
        
        # Отправляем сообщение о показе подсказки
        await callback.message.answer(
            f"💡 Показана подсказка «{hint_name}»:\n\n"
            f"<code>{hint_text}</code>\n\n"
            f"ℹ️ Оценка слова установлена на 0 за использование подсказки.",
            parse_mode="HTML"
        )
    
    # Save updated used hints
    await user_word_state.save_to_state(state)
    
    # Get display settings
    word_shown = user_word_state.get_flag("word_shown", False)
    show_hints = await get_show_hints_setting(callback, state)
    
    # Get language information for message formatting
    language_name_ru = ""
    language_name_foreign = ""
    
    language_id = current_word.get("language_id")
    if language_id:
        api_client = get_api_client_from_bot(callback.bot)
        language_response = await api_client.get_language(language_id)
        if language_response["success"] and language_response["result"]:
            language = language_response["result"]
            language_name_ru = language.get("name_ru", "")
            language_name_foreign = language.get("name_foreign", "")
    
    # Get word details
    word_number = current_word.get("word_number", 0)
    translation = current_word.get("translation", "")
    word_foreign = current_word.get("word_foreign", "")
    transcription = current_word.get("transcription", "")
    
    # Get user word data
    user_word_data = current_word.get("user_word_data", {})
    is_skipped = user_word_data.get("is_skipped", False)
    check_interval = user_word_data.get("check_interval", 0)
    next_check_date = user_word_data.get("next_check_date")
    score = user_word_data.get("score", 0)
    
    # Format main message
    message_text = format_study_word_message(
        language_name_ru,
        language_name_foreign,
        word_number,
        translation,
        is_skipped,
        score,
        check_interval,
        next_check_date,
        show_word=word_shown,
        word_foreign=word_foreign,
        transcription=transcription
    )
    
    # Add active hints using formatting utility
    hint_text_formatted = await format_used_hints(
        bot=callback.bot,
        user_id=db_user_id,
        word_id=word_id,
        current_word=current_word,
        used_hints=used_hints,
        include_header=True
    )
    
    message_text += hint_text_formatted
    
    # Create updated keyboard
    keyboard = create_word_keyboard(
        current_word, 
        word_shown=word_shown, 
        show_hints=show_hints,
        used_hints=used_hints,
    )
    
    # НОВОЕ: Возвращаемся в правильное состояние изучения после показа подсказки
    current_state = await state.get_state()
    if current_state == HintStates.viewing.state:
        # Определяем в какое состояние вернуться
        if word_shown:
            await state.set_state(StudyStates.viewing_word_details)
        else:
            await state.set_state(StudyStates.studying)
    
    # Update message
    try:
        await callback.message.edit_text(
            message_text,
            reply_markup=keyboard,
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Error updating message with toggled hints: {e}", exc_info=True)
        # If editing fails, send new message
        await callback.message.answer(
            message_text,
            reply_markup=keyboard,
            parse_mode="HTML"
        )
    
    await callback.answer()

@toggle_router.callback_query(F.data.startswith("hint_view_"), StudyStates.studying)
@toggle_router.callback_query(F.data.startswith("hint_view_"), StudyStates.viewing_word_details)
async def process_hint_view(callback: CallbackQuery, state: FSMContext):
    """
    Process callback when user wants to view a hint without toggling it in the main message.
    This creates a separate viewing experience.
    
    Args:
        callback: The callback query from Telegram
        state: The FSM state context
    """
    logger.info(f"Received hint view callback: {callback.data}")
    
    # Parse callback data using the new parser
    parsed = CallbackParser.parse_hint_action(callback.data)
    if not parsed:
        logger.error(f"Could not parse callback_data: {callback.data}")
        await callback.answer("Ошибка формата данных")
        return
    
    action, hint_type, word_id = parsed
    logger.info(f"Parsed view callback: hint_type={hint_type}, word_id={word_id}")
    
    # Validate state data
    is_valid, state_data = await validate_state_data(
        state, 
        ["current_word", "db_user_id"],
        callback,
        "Ошибка: недостаточно данных для просмотра подсказки"
    )
    
    if not is_valid:
        return
    
    # Get current word and user ID
    current_word = state_data["current_word"]
    db_user_id = state_data["db_user_id"]
    
    # Verify word ID matches current word
    current_word_id = None
    for id_field in ["id", "_id", "word_id"]:
        if id_field in current_word and current_word[id_field]:
            current_word_id = str(current_word[id_field])
            if current_word_id == word_id:
                break
    
    if not current_word_id or current_word_id != word_id:
        logger.error(f"Word ID mismatch: callback_word_id={word_id}, current_word_id={current_word_id}")
        await callback.answer("Ошибка: несоответствие ID слова")
        return
    
    # Get hint key and name
    hint_key = get_hint_key(hint_type)
    hint_name = get_hint_name(hint_type)
    hint_icon = get_hint_icon(hint_type)
    
    if not hint_key or not hint_name:
        await callback.answer("Ошибка: неизвестный тип подсказки")
        return
    
    # Get hint text
    hint_text = await get_hint_text(
        callback.bot, 
        db_user_id, 
        word_id, 
        hint_key, 
        current_word
    )
    
    if not hint_text:
        logger.error("Hint text not found")
        await callback.answer("Подсказка не найдена")
        return
    
    # НОВОЕ: Переходим в состояние просмотра подсказки
    await state.set_state(HintStates.viewing)
    
    # Get word information for context
    word_foreign = current_word.get("word_foreign", "")
    transcription = current_word.get("transcription", "")
    translation = current_word.get("translation", "")
    
    # Create viewing message
    view_message = (
        f"💡 <b>Подсказка «{hint_name}»</b>\n\n"
        f"Слово: <code>{word_foreign}</code>\n"
        f"Транскрипция: <b>[{transcription}]</b>\n"
        f"Перевод: <b>{translation}</b>\n\n"
        f"<b>{hint_icon} {hint_name}:</b>\n"
        f"<code>{hint_text}</code>\n\n"
        f"ℹ️ Для возврата к изучению нажмите кнопку ниже."
    )
    
    # Create keyboard for returning to study
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    keyboard = InlineKeyboardBuilder()
    keyboard.button(text="⬅️ Вернуться к слову", callback_data="back_to_word")
    
    # Send viewing message
    await callback.message.answer(
        view_message,
        reply_markup=keyboard.as_markup(),
        parse_mode="HTML"
    )
    
    await callback.answer(f"Показана подсказка «{hint_name}»")

@toggle_router.callback_query(F.data == "back_to_word", HintStates.viewing)
async def process_back_to_word(callback: CallbackQuery, state: FSMContext):
    """
    Process callback to return to word study from hint viewing.
    
    Args:
        callback: The callback query from Telegram
        state: The FSM state context
    """
    logger.info(f"Back to word from hint viewing from {callback.from_user.full_name}")
    
    # Get user word state to determine correct return state
    user_word_state = await UserWordState.from_state(state)
    
    if user_word_state.is_valid():
        word_shown = user_word_state.get_flag("word_shown", False)
        
        # Return to appropriate study state
        if word_shown:
            await state.set_state(StudyStates.viewing_word_details)
        else:
            await state.set_state(StudyStates.studying)
        
        # Show the study word again
        from app.bot.handlers.study.study_words import show_study_word
        await show_study_word(callback, state)
        
        await callback.answer("Возвращаемся к изучению слова")
    else:
        logger.error("Invalid user word state when returning from hint viewing")
        await callback.answer("Ошибка: недостаточно данных для возврата")
        
        # Fallback to main study state
        await state.set_state(StudyStates.studying)
        await callback.message.answer(
            "⚠️ Произошла ошибка при возврате к слову.\n"
            "Используйте команду /study для продолжения изучения."
        )
        