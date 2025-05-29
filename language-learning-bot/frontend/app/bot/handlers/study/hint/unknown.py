"""
Common functions and handlers for hint operations.
"""

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramBadRequest

from app.utils.logger import setup_logger

# Импортируем централизованные состояния
from app.bot.states.centralized_states import HintStates

# Создаем вложенный роутер для общих обработчиков
unknown_router = Router()

# Set up logging
logger = setup_logger(__name__)


@unknown_router.message(HintStates.creating)
@unknown_router.message(HintStates.editing)
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

@unknown_router.callback_query(HintStates.creating)
@unknown_router.callback_query(HintStates.editing)
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
    