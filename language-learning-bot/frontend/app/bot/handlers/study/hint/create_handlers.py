"""
Handlers for hint creation.
Now uses centralized utilities and constants.
FIXED: Corrected imports and function references, removed duplicated code.
FIXED: Added proper voice input support by importing from voice_utils.
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

# FIXED: Import voice utilities for proper voice input support
from app.utils.voice_utils import process_hint_input

from app.bot.handlers.study.study_words import show_study_word

# Создаем вложенный роутер для обработчиков создания подсказок
create_router = Router()

# Set up logging
logger = setup_logger(__name__)

# REMOVED: Local process_hint_input function - now using centralized voice utilities


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
async def process_hint_text(message: Message, state: FSMContext):
    """
    Process the hint text entered by the user as text or voice message.
    FIXED: Now uses centralized voice processing utilities and FSM states.
    
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
    
    # FIXED: Process hint input using centralized voice utilities
    hint_text = await process_hint_input(
        message, 
        hint_state.hint_name
    )
    
    if not hint_text:
        logger.error("No hint text provided")
        # Error message already handled by process_hint_input
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
    
    # IMPROVED: Check if voice input was used for custom success message
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
    
    # Determine which state to return to
    word_shown = user_word_state.get_flag("word_shown", False)
    if word_shown:
        # If word was shown, return to viewing word details state
        await state.set_state(StudyStates.viewing_word_details)
    else:
        # If word wasn't shown, return to main studying state
        await state.set_state(StudyStates.studying)
    
    # Return to studying and show word
    await show_study_word(message, state, need_new_message=True)

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

@create_router.message(HintStates.creating)
async def handle_unknown_message_during_creation(message: Message, state: FSMContext):
    """
    Handle unknown messages during hint creation.
    IMPROVED: Better handling of different message types and commands.
    
    Args:
        message: The message object from Telegram
        state: The FSM state context
    """
    logger.info(f"Unknown message during hint creation from {message.from_user.full_name}")
    
    # Check if this is a command
    from app.utils.error_utils import is_command
    
    if message.text and is_command(message.text):
        # This is a command
        command = message.text.split()[0]
        if command == "/cancel":
            # Cancel hint creation
            await cancel_hint_creation(message, state)
        else:
            # Other command - not available during hint creation
            await message.answer(
                f"⚠️ Команда {command} недоступна во время создания подсказки.\n\n"
                "Пожалуйста:\n"
                "• Введите текст подсказки\n"
                "• Или запишите голосовое сообщение\n"
                "• Или отправьте /cancel для отмены"
            )
    elif message.photo or message.document or message.video or message.sticker:
        # Unsupported media types
        await message.answer(
            "⚠️ Поддерживаются только текстовые и голосовые сообщения для создания подсказок.\n\n"
            "Пожалуйста:\n"
            "• Введите текст подсказки\n"
            "• Или запишите голосовое сообщение\n"
            "• Или используйте /cancel для отмены"
        )
    else:
        # Regular message, but not text and not voice
        if not message.text and not message.voice:
            await message.answer(
                "⚠️ Пожалуйста, отправьте текст подсказки или голосовое сообщение.\n\n"
                "Или используйте /cancel для отмены создания подсказки."
            )
        # If it's text or voice, it will be handled by the main process_hint_text handler
        