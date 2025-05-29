"""
Common functions and handlers for hint operations.
"""

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramBadRequest

from app.utils.logger import setup_logger
from app.utils.state_models import UserWordState

# Импортируем централизованные состояния
from app.bot.states.centralized_states import HintStates, StudyStates

from app.bot.handlers.study.study_words import show_study_word

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
    logger.info(f"Cancel command received in state: {current_state}")
    
    # Determine what action was cancelled
    action_cancelled = ""
    if current_state == HintStates.creating.state:
        action_cancelled = "создание подсказки"
    elif current_state == HintStates.editing.state:
        action_cancelled = "редактирование подсказки"
    elif current_state == HintStates.viewing.state:
        action_cancelled = "просмотр подсказки"
    elif current_state == HintStates.confirming_deletion.state:
        action_cancelled = "удаление подсказки"
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
