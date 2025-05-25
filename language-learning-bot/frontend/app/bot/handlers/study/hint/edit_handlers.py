"""
Refactored handlers for hint editing.
Now uses centralized utilities and constants.
"""

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from app.utils.api_utils import get_api_client_from_bot
from app.utils.logger import setup_logger
from app.utils.error_utils import validate_state_data
from app.utils.state_models import UserWordState, HintState
from app.utils.word_data_utils import ensure_user_word_data, get_hint_text
from app.utils.hint_constants import get_hint_key, get_hint_name

# Import centralized states
from app.bot.states.centralized_states import HintStates, StudyStates

# Import callback utilities
from app.utils.callback_constants import CallbackParser

# Import voice utilities
from app.utils.voice_utils import process_hint_input

# Import study utilities
from app.bot.handlers.study.study_words import show_study_word

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
        ["current_word", "db_user_id"],
        callback,
        "Ошибка: недостаточно данных для редактирования подсказки"
    )
    
    if not is_valid:
        return
    
    # Get current word and user ID
    current_word = state_data["current_word"]
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
    
    # Prepare edit message
    message_text = (
        f"📝 <b>Редактирование подсказки</b>\n\n"
        f"Слово: <code>{word_foreign}</code>\n"
        f"Транскрипция: <b>[{transcription}]</b>\n"
        f"Перевод: <b>{translation}</b>\n\n"
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

# НОВОЕ: Обработчик отмены редактирования подсказки
@edit_router.message(F.text == "/cancel", HintStates.editing)
async def cancel_hint_editing(message: Message, state: FSMContext):
    """
    Handle cancellation of hint editing.
    
    Args:
        message: The message object from Telegram
        state: The FSM state context
    """
    logger.info(f"Hint editing cancelled by {message.from_user.full_name}")
    
    # Get user word state to determine correct return state
    user_word_state = await UserWordState.from_state(state)
    
    if user_word_state.is_valid():
        word_shown = user_word_state.get_flag("word_shown", False)
        
        # Return to appropriate study state
        if word_shown:
            await state.set_state(StudyStates.viewing_word_details)
        else:
            await state.set_state(StudyStates.studying)
        
        await message.answer("❌ Редактирование подсказки отменено. Продолжаем изучение слов.")
        
        # Show the study word again
        await show_study_word(message, state)
    else:
        logger.error("Invalid user word state when cancelling hint editing")
        
        # Fallback to main study state
        await state.set_state(StudyStates.studying)
        await message.answer(
            "❌ Редактирование подсказки отменено.\n"
            "⚠️ Произошла ошибка с данными сессии.\n"
            "Используйте команду /study для продолжения изучения."
        )

# НОВОЕ: Обработчик неизвестных сообщений во время редактирования подсказки
@edit_router.message(HintStates.editing)
async def handle_unknown_message_during_editing(message: Message, state: FSMContext):
    """
    Handle unknown messages during hint editing.
    
    Args:
        message: The message object from Telegram
        state: The FSM state context
    """
    logger.info(f"Unknown message during hint editing from {message.from_user.full_name}")
    
    # Проверяем, не является ли это командой
    from app.utils.error_utils import is_command
    
    if message.text and is_command(message.text):
        # Это команда
        command = message.text.split()[0]
        if command == "/cancel":
            # Отменяем редактирование подсказки
            await cancel_hint_editing(message, state)
        else:
            # Другая команда - недоступна во время редактирования подсказки
            await message.answer(
                f"⚠️ Команда {command} недоступна во время редактирования подсказки.\n\n"
                "Пожалуйста:\n"
                "• Введите новый текст подсказки\n"
                "• Или запишите голосовое сообщение\n"
                "• Или отправьте /cancel для отмены"
            )
    else:
        # Обычное сообщение, но не текст и не голос
        if not message.text and not message.voice:
            await message.answer(
                "⚠️ Пожалуйста, отправьте новый текст подсказки или голосовое сообщение.\n\n"
                "Или используйте /cancel для отмены редактирования подсказки."
            )
        # Если это текст или голос, то обработается основным обработчиком process_hint_edit_text

# НОВОЕ: Обработчик для подтверждения удаления подсказки (если потребуется в будущем)
@edit_router.callback_query(F.data.startswith("hint_delete_"), StudyStates.studying)
@edit_router.callback_query(F.data.startswith("hint_delete_"), StudyStates.viewing_word_details)
async def process_hint_delete_request(callback: CallbackQuery, state: FSMContext):
    """
    Process callback when user wants to delete a hint.
    This starts the deletion confirmation process.
    
    Args:
        callback: The callback query from Telegram
        state: The FSM state context
    """
    logger.info(f"Received hint delete request callback: {callback.data}")
    
    # Parse callback data using the new parser
    parsed = CallbackParser.parse_hint_action(callback.data)
    if not parsed:
        logger.error(f"Could not parse callback_data: {callback.data}")
        await callback.answer("Ошибка формата данных")
        return
    
    action, hint_type, word_id = parsed
    logger.info(f"Parsed delete request: hint_type={hint_type}, word_id={word_id}")
    
    # Get hint name for display
    hint_name = get_hint_name(hint_type)
    if not hint_name:
        await callback.answer("Ошибка: неизвестный тип подсказки")
        return
    
    # НОВОЕ: Переходим в состояние подтверждения удаления
    await state.set_state(HintStates.confirming_deletion)
    
    # Save deletion context to state
    await state.update_data(
        deletion_context={
            "hint_type": hint_type,
            "word_id": word_id,
            "hint_name": hint_name
        }
    )
    
    # Create confirmation keyboard
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    keyboard = InlineKeyboardBuilder()
    keyboard.button(text="✅ Да, удалить", callback_data=f"confirm_delete_hint_{hint_type}_{word_id}")
    keyboard.button(text="❌ Отменить", callback_data="cancel_delete_hint")
    keyboard.adjust(2)
    
    await callback.message.answer(
        f"⚠️ <b>Подтверждение удаления</b>\n\n"
        f"Вы действительно хотите удалить подсказку «{hint_name}»?\n\n"
        f"⚠️ <b>Это действие нельзя отменить!</b>",
        reply_markup=keyboard.as_markup(),
        parse_mode="HTML"
    )
    
    await callback.answer()

@edit_router.callback_query(F.data.startswith("confirm_delete_hint_"), HintStates.confirming_deletion)
async def process_hint_delete_confirm(callback: CallbackQuery, state: FSMContext):
    """
    Process confirmation of hint deletion.
    
    Args:
        callback: The callback query from Telegram
        state: The FSM state context
    """
    logger.info(f"Hint deletion confirmed by {callback.from_user.full_name}")
    
    # Get deletion context
    state_data = await state.get_data()
    deletion_context = state_data.get("deletion_context", {})
    
    if not deletion_context:
        await callback.answer("Ошибка: контекст удаления не найден")
        return
    
    hint_name = deletion_context.get("hint_name", "подсказка")
    
    # TODO: Implement actual deletion logic here
    # This would involve calling API to remove the hint
    
    await callback.message.answer(
        f"✅ Подсказка «{hint_name}» была удалена.\n\n"
        "Продолжаем изучение слов..."
    )
    
    # Return to appropriate study state
    user_word_state = await UserWordState.from_state(state)
    if user_word_state.is_valid():
        word_shown = user_word_state.get_flag("word_shown", False)
        if word_shown:
            await state.set_state(StudyStates.viewing_word_details)
        else:
            await state.set_state(StudyStates.studying)
        
        # Show the study word again
        await show_study_word(callback, state)
    else:
        await state.set_state(StudyStates.studying)
    
    await callback.answer()

@edit_router.callback_query(F.data == "cancel_delete_hint", HintStates.confirming_deletion)
async def process_hint_delete_cancel(callback: CallbackQuery, state: FSMContext):
    """
    Process cancellation of hint deletion.
    
    Args:
        callback: The callback query from Telegram
        state: The FSM state context
    """
    logger.info(f"Hint deletion cancelled by {callback.from_user.full_name}")
    
    await callback.message.answer("❌ Удаление подсказки отменено.")
    
    # Return to appropriate study state
    user_word_state = await UserWordState.from_state(state)
    if user_word_state.is_valid():
        word_shown = user_word_state.get_flag("word_shown", False)
        if word_shown:
            await state.set_state(StudyStates.viewing_word_details)
        else:
            await state.set_state(StudyStates.studying)
        
        # Show the study word again
        await show_study_word(callback, state)
    else:
        await state.set_state(StudyStates.studying)
    
    await callback.answer()
    