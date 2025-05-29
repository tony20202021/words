
"""
Handlers for hint creation.
Now uses centralized utilities and constants.
FIXED: Corrected imports and function references, removed duplicated code.
"""

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from app.utils.api_utils import get_api_client_from_bot
from app.utils.logger import setup_logger
from app.utils.error_utils import validate_state_data
from app.utils.state_models import UserWordState, HintState
from app.utils.word_data_utils import ensure_user_word_data
from app.utils.hint_constants import get_all_hint_types, get_hint_key, get_hint_name

# Import centralized states
from app.bot.states.centralized_states import HintStates, StudyStates

# Import callback utilities
from app.utils.callback_constants import CallbackParser

from app.bot.handlers.study.study_words import show_study_word

# Создаем вложенный роутер для обработчиков создания подсказок
create_router = Router()

# Set up logging
logger = setup_logger(__name__)

# Простая обработка текста (без голосовых утилит)
async def process_hint_input(message: Message, hint_name: str) -> str:
    """
    Process hint input from text message.
    
    Args:
        message: The message object from Telegram
        hint_name: Name of the hint being processed
        
    Returns:
        str: Processed hint text or empty string if invalid
    """
    if message.text:
        hint_text = message.text.strip()
        if hint_text:
            return hint_text
    
    await message.answer("❌ Пожалуйста, введите текст подсказки.")
    return ""


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
        ["current_word", "db_user_id"],
        callback,
        "Ошибка: недостаточно данных для создания подсказки"
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
async def process_hint_text(message: Message, state: FSMContext):
    """
    Process the hint text entered by the user as text or voice message.
    Now uses centralized voice processing utilities and FSM states.
    
    Args:
        message: The message object from Telegram
        state: The FSM state context
    """
    # Load hint state from FSM
    hint_state = await HintState.from_state(state)
    
    # Validate hint state
    if not hint_state.is_valid():
        logger.error("Invalid hint state")
        await message.answer("❌ Ошибка: недостаточно данных для создания подсказки. Используйте /cancel для отмены.")
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
        logger.error("No hint text provided")
        await message.answer("❌ Пожалуйста, введите текст подсказки или запишите голосовое сообщение.")
        return
    
    # Save hint to database
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
        logger.error("Failed to save hint to database")
        return
    
    # Update word state
    user_word_state.set_flag("word_shown", True)
    
    # Update current word data in state with new hint
    if user_word_state.word_data:
        # If user_word_data exists, update there
        user_word_data = user_word_state.word_data.get("user_word_data", {})
        if not user_word_data:
            user_word_state.word_data["user_word_data"] = {}
            
        user_word_state.word_data["user_word_data"][hint_state.hint_key] = hint_text
        
        # Add hint to used hints
        used_hints = user_word_state.get_flag("used_hints", [])
        hint_type = hint_state.get_hint_type()
        if hint_type and hint_type not in used_hints:
            used_hints.append(hint_type)
            user_word_state.set_flag("used_hints", used_hints)
        
        # Save updated word data to state
        await user_word_state.save_to_state(state)
    
    # Send success message
    await message.answer(
        f"✅ Подсказка «{hint_state.hint_name}» успешно создана!\n\n"
        f"💡 Текст подсказки:\n<code>{hint_text}</code>\n\n"
        "Продолжаем изучение слов...",
        parse_mode="HTML"
    )
    
    # НОВОЕ: Определяем в какое состояние вернуться
    word_shown = user_word_state.get_flag("word_shown", False)
    if word_shown:
        # Если слово было показано, возвращаемся в состояние просмотра деталей
        await state.set_state(StudyStates.viewing_word_details)
    else:
        # Если слово не было показано, возвращаемся в основное состояние изучения
        await state.set_state(StudyStates.studying)
    
    # Return to studying and show word
    await show_study_word(message, state)

# НОВОЕ: Обработчик отмены создания подсказки
@create_router.message(F.text == "/cancel", HintStates.creating)
async def cancel_hint_creation(message: Message, state: FSMContext):
    """
    Handle cancellation of hint creation.
    
    Args:
        message: The message object from Telegram
        state: The FSM state context
    """
    logger.info(f"Hint creation cancelled by {message.from_user.full_name}")
    
    # Get user word state to determine correct return state
    user_word_state = await UserWordState.from_state(state)
    
    if user_word_state.is_valid():
        word_shown = user_word_state.get_flag("word_shown", False)
        
        # Return to appropriate study state
        if word_shown:
            await state.set_state(StudyStates.viewing_word_details)
        else:
            await state.set_state(StudyStates.studying)
        
        await message.answer("❌ Создание подсказки отменено. Продолжаем изучение слов.")
        
        # Show the study word again
        await show_study_word(message, state)
    else:
        logger.error("Invalid user word state when cancelling hint creation")
        
        # Fallback to main study state
        await state.set_state(StudyStates.studying)
        await message.answer(
            "❌ Создание подсказки отменено.\n"
            "⚠️ Произошла ошибка с данными сессии.\n"
            "Используйте команду /study для продолжения изучения."
        )

# НОВОЕ: Обработчик неизвестных сообщений во время создания подсказки
@create_router.message(HintStates.creating)
async def handle_unknown_message_during_creation(message: Message, state: FSMContext):
    """
    Handle unknown messages during hint creation.
    
    Args:
        message: The message object from Telegram
        state: The FSM state context
    """
    logger.info(f"Unknown message during hint creation from {message.from_user.full_name}")
    
    # Проверяем, не является ли это командой
    from app.utils.error_utils import is_command
    
    if message.text and is_command(message.text):
        # Это команда
        command = message.text.split()[0]
        if command == "/cancel":
            # Отменяем создание подсказки
            await cancel_hint_creation(message, state)
        else:
            # Другая команда - недоступна во время создания подсказки
            await message.answer(
                f"⚠️ Команда {command} недоступна во время создания подсказки.\n\n"
                "Пожалуйста:\n"
                "• Введите текст подсказки\n"
                "• Или запишите голосовое сообщение\n"
                "• Или отправьте /cancel для отмены"
            )
    else:
        # Обычное сообщение, но не текст и не голос
        if not message.text and not message.voice:
            await message.answer(
                "⚠️ Пожалуйста, отправьте текст подсказки или голосовое сообщение.\n\n"
                "Или используйте /cancel для отмены создания подсказки."
            )
        # Если это текст или голос, то обработается основным обработчиком process_hint_text
        