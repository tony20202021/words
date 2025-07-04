"""
Common functions and handlers for hint operations.
"""

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.fsm.context import FSMContext

from app.utils.logger import setup_logger
from app.utils.state_models import UserWordState
from app.bot.states.centralized_states import HintStates, StudyStates
from app.bot.handlers.study.study_words import show_study_word
from app.utils.state_models import UserWordState, HintState
from app.utils.voice_utils import process_hint_input
from app.utils.word_data_utils import ensure_user_word_data

# Создаем вложенный роутер для общих обработчиков
common_router = Router()

# Set up logging
logger = setup_logger(__name__)

@common_router.message(Command("cancel"), HintStates.creating, flags={"priority": 100})  # высокий приоритет
@common_router.message(Command("cancel"), HintStates.editing, flags={"priority": 100})   # высокий приоритет
async def cmd_cancel_hint(message: Message, state: FSMContext):
    """
    Handle the /cancel command to abort hint creation/editing/viewing/deletion.
    
    Args:
        message: The message object from Telegram
        state: The FSM state context
    """
    # Get current state name
    current_state = await state.get_state()
    logger.info(f"Cancel 1 command received in state: {current_state}")
    
    # Determine what action was cancelled
    action_cancelled = ""
    if current_state == HintStates.creating.state:
        action_cancelled = "создание подсказки"
    elif current_state == HintStates.editing.state:
        action_cancelled = "редактирование подсказки"
    else:
        action_cancelled = "действие с подсказкой"
    
    # Get user word state to determine correct return state
    user_word_state = await UserWordState.from_state(state)

    if user_word_state.is_valid():
        word_shown = user_word_state.get_flag("word_shown", False)
        
        # Return to appropriate study state
        if word_shown:
            await state.set_state(StudyStates.viewing_word_details)
        else:
            await state.set_state(StudyStates.studying)
        
        await message.answer(f"✅ Отменено {action_cancelled}. Продолжаем изучение слов.")
        
        try:
            # Attempt to show the study word again
            await show_study_word(message, state)
        except Exception as e:
            logger.error(f"Error showing study word after cancel: {e}", exc_info=True)
            await message.answer("Произошла ошибка при возврате к изучению. Используйте команду /study чтобы продолжить.")
    else:
        logger.error("Invalid user word state when cancelling hint operation")
        
        # Fallback to main study state
        await state.set_state(StudyStates.studying)
        await message.answer(
            f"✅ Отменено {action_cancelled}.\n"
            "⚠️ Произошла ошибка с данными сессии.\n"
            "Используйте команду /study для продолжения изучения."
        )

@common_router.message(Command("help"), HintStates.creating)
@common_router.message(Command("help"), HintStates.editing)
async def cmd_help_during_hint_operations(message: Message, state: FSMContext):
    """
    Handle the /help command during hint operations.
    
    Args:
        message: The message object from Telegram
        state: The FSM state context
    """
    current_state = await state.get_state()
    logger.info(f"Help command during hint operation from {message.from_user.full_name}, state: {current_state}")
    
    help_text = "💡 <b>Помощь по работе с подсказками:</b>\n\n"
    
    if current_state == HintStates.creating.state:
        help_text += (
            "Вы создаете подсказку для слова.\n\n"
            "<b>Что можно делать:</b>\n"
            "• Введите текст подсказки\n"
            "• Запишите голосовое сообщение\n"
            "• /cancel - отменить создание\n\n"
            "<b>Типы подсказок:</b>\n"
            "🧠 Ассоциация на русском - связь со значением\n"
            "💡 Ассоциация для фонетики - помощь с произношением\n"
            "🎵 Звучание по слогам - разбивка на части\n"
            "✍️ Ассоциация для написания - помощь с запоминанием букв"
        )
    elif current_state == HintStates.editing.state:
        help_text += (
            "Вы редактируете подсказку для слова.\n\n"
            "<b>Что можно делать:</b>\n"
            "• Введите новый текст подсказки\n"
            "• Запишите новое голосовое сообщение\n"
            "• /cancel - отменить редактирование\n\n"
            "<b>Совет:</b> Нажмите на текущую подсказку, чтобы скопировать её и отредактировать."
        )
    elif current_state == HintStates.viewing.state:
        help_text += (
            "Вы просматриваете подсказку.\n\n"
            "<b>Что можно делать:</b>\n"
            "• Используйте кнопку \"Назад\" для возврата к слову\n"
            "• /cancel - вернуться к изучению\n\n"
            "<b>Напоминание:</b> Использование подсказки устанавливает оценку слова на 0."
        )
    else:
        help_text += "Используйте /cancel для возврата к изучению слов."
    
    await message.answer(help_text, parse_mode="HTML")



async def process_hint_text(message: Message, state: FSMContext):
    """
    Process the edited hint text entered by the user as text or voice message.
    Now uses centralized voice processing utilities and FSM states.
    
    Args:
        message: The message object from Telegram
        state: The FSM state context
    """
    logger.info(f"Hint text by {message.from_user.full_name}")

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

    return user_word_state, hint_state, hint_text
  
  
async def return_after_hint(message: Message, state: FSMContext, user_word_state: UserWordState):
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

