"""
Refactored handlers for hint editing.
Now uses centralized utilities and constants.
"""

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.filters import Command

from app.utils.logger import setup_logger
from app.utils.error_utils import validate_state_data
from app.utils.state_models import HintState
from app.utils.word_data_utils import get_hint_text
from app.utils.hint_constants import get_hint_key, get_hint_name
from app.bot.states.centralized_states import HintStates, StudyStates
from app.utils.callback_constants import CallbackParser
from app.bot.handlers.study.hint.common import return_after_hint, process_hint_text

# Создаем вложенный роутер для обработчиков редактирования
edit_router = Router()

# Set up logging
logger = setup_logger(__name__)


@edit_router.callback_query(F.data.startswith("hint_edit_"), StudyStates.studying)
@edit_router.callback_query(F.data.startswith("hint_edit_"), StudyStates.viewing_word_details)
async def process_hint_edit(callback: CallbackQuery, state: FSMContext):
    """
    Process callback when user wants to edit an existing hint.
    Now uses improved callback parsing and FSM states.
    
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
        ["word_data", "db_user_id"],
        callback,
        "Ошибка: недостаточно данных для редактирования подсказки"
    )
    
    if not is_valid:
        logger.error(f"not is_valid")
        return
    
    # Get current word and user ID
    current_word = state_data["word_data"]
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
    radicals = current_word.get("radicals", "")
    references = current_word.get("references", "")
    tones = current_word.get("tones", "")
    sounds = current_word.get("sounds", "")    
    
    # Prepare edit message
    message_text = (
        f"📝 <b>Редактирование подсказки</b>\n\n"
        f"Слово: <code>{word_foreign}</code>\n"
        f"Транскрипция: <b>[{transcription}]</b>\n"
        f"Перевод: <b>{translation}</b>\n"
        f"Радикалы: <b>{radicals}</b>\n"
        f"Ссылки: <b>{references}</b>\n"
        f"Тоны: <b>{tones}</b>\n\n"
        f"Звуки: <b>{sounds}</b>\n\n"        
    )
    
    if current_hint_text:
        message_text += (
            f"💡 Подсказка <b>«{hint_name}»</b>\n\n"
            f"<b>Текущий текст:</b>\n"
            f"<code>{current_hint_text}</code>\n\n"
            f"📋 Нажмите на текст выше, чтобы скопировать.\n\n"
            f"Отправьте новый текст подсказки,\n"
            f"или запишите голосовое сообщение,\n"
            f"или используйте /cancel для отмены."
        )
    else:
        message_text += (
            f"💡 Подсказка <b>«{hint_name}»</b>\n\n"
            f"⚠️ Подсказка пуста или не найдена.\n\n"
            f"Отправьте новый текст подсказки,\n"
            f"или запишите голосовое сообщение,\n"
            f"или используйте /cancel для отмены."
        )
    
    await callback.message.answer(message_text, parse_mode="HTML")
    await callback.answer(f"Редактирование подсказки «{hint_name}»")

@edit_router.message(HintStates.editing)
async def process_hint_edit_text(message: Message, state: FSMContext):
    """
    Process the edited hint text entered by the user as text or voice message.
    Now uses centralized voice processing utilities and FSM states.
    
    Args:
        message: The message object from Telegram
        state: The FSM state context
    """
    logger.info(f"Hint text edit by {message.from_user.full_name}")

    user_word_state, hint_state, hint_text = await process_hint_text(message, state)

    # Show success message with comparison
    old_hint = hint_state.current_hint_text or ""
    if old_hint != hint_text:
        await message.answer(
            f"✅ Подсказка «{hint_state.hint_name}» успешно обновлена!\n\n"
            f"<b>Было:</b>\n<code>{old_hint}</code>\n\n"
            f"<b>Стало:</b>\n<code>{hint_text}</code>\n\n"
            "Продолжаем изучение слов...",
            parse_mode="HTML",
        )
    else:
        await message.answer(
            f"✅ Подсказка «{hint_state.hint_name}» сохранена без изменений.\n\n"
            f"<b>Текст подсказки:</b>\n<code>{hint_text}</code>\n\n"
            "Продолжаем изучение слов...",
            parse_mode="HTML",
        )
    
    await return_after_hint(message, state, user_word_state)
