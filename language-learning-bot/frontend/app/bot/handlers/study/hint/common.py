"""
Common functions and handlers for hint operations.
"""

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram.dispatcher.router import Router
from aiogram.dispatcher.event.bases import SkipHandler

from app.utils.logger import setup_logger
from app.bot.handlers.study.study_states import HintStates, StudyStates
from app.bot.handlers.study.study_words import show_study_word

# Создаем вложенный роутер для общих обработчиков
cancel_router = Router()

# Set up logging
logger = setup_logger(__name__)

@cancel_router.message(Command("cancel"), HintStates.creating)
@cancel_router.message(Command("cancel"), HintStates.editing)
async def cmd_cancel_hint(message: Message, state: FSMContext):
    """
    Handle the /cancel command to abort hint creation/editing.
    
    Args:
        message: The message object from Telegram
        state: The FSM state context
    """
    # Get current state name
    current_state_name = await state.get_state()
    
    # Check if we're in a hint state
    if current_state_name in ["HintStates:creating", "HintStates:editing"]:
        # Return to studying state
        await state.set_state(StudyStates.studying)
        await message.answer("✅ Отменено создание/редактирование подсказки. Продолжаем изучение слов.")
        await show_study_word(message, state)
    else:
        await message.answer("⚠️ Нет активного процесса создания подсказки для отмены.")
    
    # Важно: предотвращаем дальнейшую обработку этого сообщения другими обработчиками
    raise SkipHandler()