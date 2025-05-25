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
cancel_router = Router()

# Set up logging
logger = setup_logger(__name__)

@cancel_router.message(Command("cancel"), HintStates.creating, flags={"priority": 100})  # высокий приоритет
@cancel_router.message(Command("cancel"), HintStates.editing, flags={"priority": 100})   # высокий приоритет
@cancel_router.message(Command("cancel"), HintStates.viewing, flags={"priority": 100})   # высокий приоритет
@cancel_router.message(Command("cancel"), HintStates.confirming_deletion, flags={"priority": 100})  # высокий приоритет
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

# НОВОЕ: Обработчик для навигации "назад к слову"
@cancel_router.callback_query(F.data == "back_to_word", HintStates.viewing)
async def process_back_to_word_from_viewing(callback: CallbackQuery, state: FSMContext):
    """
    Process callback to return to word study from hint viewing state.
    
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

# НОВОЕ: Обработчик help команды в состояниях подсказок
@cancel_router.message(Command("help"), HintStates.creating)
@cancel_router.message(Command("help"), HintStates.editing)
@cancel_router.message(Command("help"), HintStates.viewing)
@cancel_router.message(Command("help"), HintStates.confirming_deletion)
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
    elif current_state == HintStates.confirming_deletion.state:
        help_text += (
            "Вы подтверждаете удаление подсказки.\n\n"
            "<b>Что можно делать:</b>\n"
            "• Нажмите \"Да\" для подтверждения удаления\n"
            "• Нажмите \"Отменить\" для отмены\n"
            "• /cancel - отменить удаление\n\n"
            "⚠️ <b>Внимание:</b> Удаление подсказки нельзя отменить!"
        )
    else:
        help_text += "Используйте /cancel для возврата к изучению слов."
    
    await message.answer(help_text, parse_mode="HTML")

# НОВОЕ: Обработчик неизвестных команд в состояниях подсказок
@cancel_router.message(HintStates.creating)
@cancel_router.message(HintStates.editing)
@cancel_router.message(HintStates.viewing)
@cancel_router.message(HintStates.confirming_deletion)
async def handle_unknown_message_during_hint_operations(message: Message, state: FSMContext):
    """
    Handle unknown messages during hint operations.
    This is a fallback handler for states where specific handlers don't catch the message.
    
    Args:
        message: The message object from Telegram
        state: The FSM state context
    """
    current_state = await state.get_state()
    logger.info(f"Unknown message during hint operation: state={current_state}, from={message.from_user.full_name}")
    
    # Проверяем, не является ли это командой
    from app.utils.error_utils import is_command
    
    if message.text and is_command(message.text):
        command = message.text.split()[0]
        
        # Известные команды уже обработаны выше, это неизвестная команда
        await message.answer(
            f"⚠️ Команда {command} недоступна во время работы с подсказками.\n\n"
            "Доступные команды:\n"
            "/cancel - отменить текущее действие\n"
            "/help - получить помощь"
        )
    else:
        # Обычное сообщение в неподходящем состоянии
        state_descriptions = {
            HintStates.creating.state: "создания подсказки",
            HintStates.editing.state: "редактирования подсказки", 
            HintStates.viewing.state: "просмотра подсказки",
            HintStates.confirming_deletion.state: "подтверждения удаления"
        }
        
        state_desc = state_descriptions.get(current_state, "работы с подсказкой")
        
        # Для viewing и confirming_deletion не ожидаем текстовых сообщений
        if current_state in [HintStates.viewing.state, HintStates.confirming_deletion.state]:
            await message.answer(
                f"⚠️ Используйте кнопки под сообщениями во время {state_desc}.\n\n"
                "Или воспользуйтесь командой /cancel для отмены."
            )
        else:
            # Для creating и editing подсказываем что ожидается
            await message.answer(
                f"⚠️ Сейчас ожидается ввод текста подсказки во время {state_desc}.\n\n"
                "Отправьте текст или голосовое сообщение,\n"
                "либо используйте /cancel для отмены."
            )

# НОВОЕ: Обработчик для общих callback во время операций с подсказками
@cancel_router.callback_query(HintStates.creating)
@cancel_router.callback_query(HintStates.editing)
async def handle_unexpected_callback_during_hint_input(callback: CallbackQuery, state: FSMContext):
    """
    Handle unexpected callbacks during hint input states.
    
    Args:
        callback: The callback query from Telegram
        state: The FSM state context
    """
    current_state = await state.get_state()
    logger.info(f"Unexpected callback during hint input: state={current_state}, data={callback.data}")
    
    state_descriptions = {
        HintStates.creating.state: "создания подсказки",
        HintStates.editing.state: "редактирования подсказки"
    }
    
    state_desc = state_descriptions.get(current_state, "ввода подсказки")
    
    await callback.answer(
        f"⚠️ Сейчас ожидается текст подсказки. Отправьте сообщение или используйте /cancel.",
        show_alert=True
    )
    
    await callback.message.answer(
        f"⚠️ Кнопки недоступны во время {state_desc}.\n\n"
        "Пожалуйста:\n"
        "• Отправьте текст подсказки\n"
        "• Или запишите голосовое сообщение\n"
        "• Или используйте /cancel для отмены"
    )
    