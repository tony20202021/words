"""
Handlers for hint creation.
Now uses centralized utilities and constants.
FIXED: Corrected imports and function references, removed duplicated code.
FIXED: Added proper voice input support by importing from voice_utils.
"""

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from app.utils.logger import setup_logger
from app.utils.error_utils import validate_state_data
from app.utils.state_models import HintState
from app.utils.hint_constants import get_hint_key, get_hint_name
from app.bot.states.centralized_states import HintStates, StudyStates
from app.utils.callback_constants import CallbackParser
from app.bot.handlers.study.hint.common import return_after_hint, process_hint_text

# Создаем вложенный роутер для обработчиков создания подсказок
create_router = Router()

# Set up logging
logger = setup_logger(__name__)

@create_router.callback_query(F.data.startswith("hint_create_"), StudyStates.studying)
@create_router.callback_query(F.data.startswith("hint_create_"), StudyStates.viewing_word_details)
async def process_hint_create(callback: CallbackQuery, state: FSMContext):
    """
    Process callback when user wants to create a new hint.
    Now uses improved callback parsing and FSM states.
    
    Args:
        callback: The callback query from Telegram
        state: The FSM state context
    """
    logger.info(f"Received hint create callback: {callback.data}")
    
    # Parse callback data using the new parser
    parsed = CallbackParser.parse_hint_action(callback.data)
    if not parsed:
        logger.error(f"Could not parse callback_data: {callback.data}")
        await callback.answer("Ошибка формата данных подсказки")
        return
    
    action, hint_type, word_id = parsed
    logger.info(f"Parsed callback: action={action}, hint_type={hint_type}, word_id={word_id}")
    
    # Validate state data
    is_valid, state_data = await validate_state_data(
        state, 
        ["word_data"],
        callback,
        "Ошибка: недостаточно данных для создания подсказки"
    )
    
    if not is_valid:
        logger.error(f"not is_valid")
        return
    
    # Get current word and user ID
    current_word = state_data["word_data"]
    
    # Verify word ID matches current word
    current_word_id = None
    for id_field in ["id", "_id", "word_id"]:
        if id_field in current_word and current_word[id_field]:
            current_word_id = str(current_word[id_field])
            if current_word_id == word_id:
                break
    
    if not current_word_id or current_word_id != word_id:
        logger.error(f"Word ID mismatch: callback_word_id={word_id}, current_word_id={current_word_id}")
        await callback.answer("Ошибка: несоответствие ID слова. Пожалуйста, обновите слово.")
        return
    
    # Get hint key and name
    hint_key = get_hint_key(hint_type)
    hint_name = get_hint_name(hint_type)
    
    if not hint_key or not hint_name:
        await callback.answer("Ошибка: неизвестный тип подсказки")
        return
    
    # Create hint state
    hint_state = HintState(
        hint_key=hint_key,
        hint_name=hint_name,
        hint_word_id=word_id
    )
    
    # Save to state using centralized state
    await hint_state.save_to_state(state)
    await state.set_state(HintStates.creating)
    
    # Get word info for display
    word_foreign = current_word.get("word_foreign")
    transcription = current_word.get("transcription", "")
    translation = current_word.get("translation", "")
    
    # Send creation prompt
    await callback.message.answer(
        f"📝 <b>Создание подсказки</b>\n\n"
        f"Слово: <code>{word_foreign}</code>\n"
        f"Транскрипция: <b>[{transcription}]</b>\n"
        f"Перевод: <b>{translation}</b>\n\n"
        f"💡 Создание подсказки типа «{hint_name}»\n\n"
        f"Пожалуйста, введите текст подсказки,\n"
        f"или запишите голосовое сообщение,\n"
        f"или отправьте /cancel для отмены:",
        parse_mode="HTML",
    )
    
    await callback.answer(f"Создание подсказки «{hint_name}»")

@create_router.message(HintStates.creating)
async def process_hint_create_text(message: Message, state: FSMContext):
    """
    Process the hint text entered by the user as text or voice message.
    
    Args:
        message: The message object from Telegram
        state: The FSM state context
    """
    logger.info(f"Hint text create by {message.from_user.full_name}")

    user_word_state, hint_state, hint_text = await process_hint_text(message, state)
    
    # Check if voice input was used for custom success message
    if message.voice:
        await message.answer(
            f"✅ Подсказка «{hint_state.hint_name}» успешно создана из голосового сообщения!\n\n"
            f"💡 Распознанный текст подсказки:\n<code>{hint_text}</code>\n\n"
            "Продолжаем изучение слов...",
            parse_mode="HTML"
        )
    else:
        await message.answer(
            f"✅ Подсказка «{hint_state.hint_name}» успешно создана!\n\n"
            f"💡 Текст подсказки:\n<code>{hint_text}</code>\n\n"
            "Продолжаем изучение слов...",
            parse_mode="HTML"
        )
    
    await return_after_hint(message, state, user_word_state)

 