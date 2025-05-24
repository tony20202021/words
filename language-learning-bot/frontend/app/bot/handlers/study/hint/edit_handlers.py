"""
Refactored handlers for hint editing.
Now uses centralized utilities and constants.
"""

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from app.utils.api_utils import get_api_client_from_bot
from app.utils.logger import setup_logger
from app.utils.error_utils import validate_state_data
from app.utils.state_models import UserWordState, HintState
from app.utils.word_data_utils import ensure_user_word_data, get_hint_text
from app.utils.hint_constants import get_hint_key, get_hint_name

# Import centralized states
from app.bot.states.centralized_states import HintStates, StudyStates

# Import callback utilities
from app.utils.callback_constants import CallbackParser

# Import voice utilities
from app.utils.voice_utils import process_hint_input

# Import study utilities
from app.bot.handlers.study.study_words import show_study_word

# Создаем вложенный роутер для обработчиков редактирования
edit_router = Router()

# Set up logging
logger = setup_logger(__name__)


@edit_router.callback_query(F.data.startswith("hint_edit_"))
async def process_hint_edit(callback: CallbackQuery, state: FSMContext):
    """
    Process callback when user wants to edit an existing hint.
    Now uses improved callback parsing.
    
    Args:
        callback: The callback query from Telegram
        state: The FSM state context
    """
    logger.info(f"Received hint edit callback: {callback.data}")
    
    # Parse callback data using the new parser
    parsed = CallbackParser.parse_hint_action(callback.data)
    if not parsed:
        logger.error(f"Could not parse callback_data: {callback.data}")
        await callback.answer("Ошибка формата данных")
        return
    
    action, hint_type, word_id = parsed
    logger.info(f"Parsed callback: action={action}, hint_type={hint_type}, word_id={word_id}")
    
    # Validate state data
    is_valid, state_data = await validate_state_data(
        state, 
        ["current_word", "db_user_id"],
        callback,
        "Ошибка: недостаточно данных для редактирования подсказки"
    )
    
    if not is_valid:
        return
    
    # Get current word and user ID
    current_word = state_data["current_word"]
    db_user_id = state_data["db_user_id"]
    
    # Verify word ID matches current word
    current_word_id = current_word.get("id") or current_word.get("_id") or current_word.get("word_id")
    if str(current_word_id) != word_id:
        logger.error(f"Word ID mismatch: callback_word_id={word_id}, current_word_id={current_word_id}")
        await callback.answer("Ошибка: несоответствие ID слова")
        return
    
    # Get hint key and name
    hint_key = get_hint_key(hint_type)
    hint_name = get_hint_name(hint_type)
    
    if not hint_key or not hint_name:
        await callback.answer("Ошибка: неизвестный тип подсказки")
        return
    
    # Get current hint text
    current_hint_text = await get_hint_text(
        callback.bot, 
        db_user_id, 
        word_id, 
        hint_key, 
        current_word
    )
    
    # Create hint state
    hint_state = HintState(
        hint_key=hint_key,
        hint_name=hint_name,
        hint_word_id=word_id,
        current_hint_text=current_hint_text
    )
    
    # Save to state using centralized state
    await hint_state.save_to_state(state)
    await state.set_state(HintStates.editing)
    
    # Get word info for display
    word_foreign = current_word.get("word_foreign")
    transcription = current_word.get("transcription", "")
    translation = current_word.get("translation", "")
    
    # Prepare edit message
    message_text = (
        f"📝 Редактирование подсказки\n\n"
        f"Слово: <b>{word_foreign}</b>\n"
        f"Транскрипция: <b>[{transcription}]</b>\n"
        f"Перевод:\n<b>{translation}</b>\n\n"
    )
    
    if current_hint_text:
        message_text += (
            f"Подсказка <b>«{hint_name}»</b>\n\n"
            f"<code>{current_hint_text}</code>\n\n"
            f"📋 Нажмите на текст, чтобы скопировать.\n"
            f"Либо отправьте новый текст подсказки.\n\n"
            f"Либо запишите голосовое сообщение.\n"
            f"Для отмены редактирования отправьте /cancel"
        )
    else:
        message_text += (
            f"Отправьте новый текст подсказки.\n"
            f"Либо запишите голосовое сообщение.\n"
            f"Для отмены редактирования отправьте /cancel"
        )
    
    await callback.message.answer(message_text, parse_mode="HTML")
    await callback.answer()


@edit_router.message(HintStates.editing)
async def process_hint_edit_text(message: Message, state: FSMContext):
    """
    Process the edited hint text entered by the user as text or voice message.
    Now uses centralized voice processing utilities.
    
    Args:
        message: The message object from Telegram
        state: The FSM state context
    """
    # Load hint state from FSM
    hint_state = await HintState.from_state(state)
    
    # Validate hint state
    if not hint_state.is_valid():
        logger.error("Invalid hint state")
        await message.answer("❌ Ошибка: недостаточно данных для редактирования подсказки. Используйте /cancel для отмены.")
        return
    
    # Load user word state
    user_word_state = await UserWordState.from_state(state)
    
    # Validate user word state
    if not user_word_state.is_valid():
        logger.error("Invalid user word state")
        await message.answer("❌ Ошибка: недостаточно данных о пользователе или слове. Используйте /cancel для отмены.")
        return
    
    # Process hint input using voice utilities
    hint_text = await process_hint_input(
        message, 
        hint_state.hint_name
    )
    
    if not hint_text:
        return  # Error already handled by voice utilities
    
    # Save updated hint to database
    update_data = {hint_state.hint_key: hint_text}
    
    success, result = await ensure_user_word_data(
        message.bot,
        user_word_state.user_id,
        hint_state.hint_word_id,
        update_data,
        user_word_state.word_data,
        message
    )
    
    if not success:
        logger.error("Failed to update hint in database")
        return
    
    # Update current word data in state with new hint
    if user_word_state.word_data:
        # If user_word_data exists, update there
        user_word_data = user_word_state.word_data.get("user_word_data", {})
        if not user_word_data:
            user_word_state.word_data["user_word_data"] = {}
            
        user_word_state.word_data["user_word_data"][hint_state.hint_key] = hint_text
        
        # Add hint to used hints if not already there
        used_hints = user_word_state.get_flag("used_hints", [])
        hint_type = hint_state.get_hint_type()
        if hint_type and hint_type not in used_hints:
            used_hints.append(hint_type)
            user_word_state.set_flag("used_hints", used_hints)
        
        # Save updated word data to state
        await user_word_state.save_to_state(state)
    
    # Show success message with comparison
    old_hint = hint_state.current_hint_text or ""
    if old_hint != hint_text:
        await message.answer(
            f"✅ Подсказка «{hint_state.hint_name}» успешно обновлена!\n\n"
            f"Было:\n<code>{old_hint}</code>\n\n"
            f"Стало:\n<code>{hint_text}</code>\n\n"
            "Продолжаем изучение слов...",
            parse_mode="HTML",
        )
    else:
        await message.answer(
            f"✅ Подсказка «{hint_state.hint_name}» сохранена без изменений.\n\n"
            f"Текст подсказки:\n<code>{hint_text}</code>\n\n"
            "Продолжаем изучение слов...",
            parse_mode="HTML",
        )
    
    # Return to studying state using centralized state
    await state.set_state(StudyStates.studying)
    await show_study_word(message, state)
    