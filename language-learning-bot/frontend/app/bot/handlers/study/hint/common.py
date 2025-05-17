"""
Common functions and handlers for hint operations.
"""

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramBadRequest

from app.utils.logger import setup_logger
from app.bot.handlers.study.study_states import HintStates, StudyStates
from app.bot.handlers.study.study_words import show_study_word

# Создаем вложенный роутер для общих обработчиков
cancel_router = Router()

# Set up logging
logger = setup_logger(__name__)

@cancel_router.message(Command("cancel"), HintStates.creating, flags={"priority": 100})  # высокий приоритет
@cancel_router.message(Command("cancel"), HintStates.editing, flags={"priority": 100})  # высокий приоритет
async def cmd_cancel_hint(message: Message, state: FSMContext):
    """
    Handle the /cancel command to abort hint creation/editing.
    
    Args:
        message: The message object from Telegram
        state: The FSM state context
    """
    # Get current state name
    current_state = await state.get_state()
    logger.info(f"Cancel command received in state: {current_state}")
    
    # Check if we're in a hint state
    if current_state in ["HintStates:creating", "HintStates:editing"]:
        # Return to studying state
        await state.set_state(StudyStates.studying)
        await message.answer("✅ Отменено создание/редактирование подсказки. Продолжаем изучение слов.")
        
        try:
            # Attempt to show the study word again
            await show_study_word(message, state)
        except Exception as e:
            logger.error(f"Error showing study word after cancel: {e}", exc_info=True)
            await message.answer("Произошла ошибка при возврате к изучению. Используйте команду /study чтобы продолжить.")
    else:
        await message.answer("⚠️ Нет активного процесса создания подсказки для отмены.")