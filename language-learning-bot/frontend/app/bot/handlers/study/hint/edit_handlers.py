"""
Handlers for hint editing.
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
from app.bot.handlers.study.study_states import HintStates, StudyStates
from app.bot.handlers.study.study_words import show_study_word

# Создаем вложенный роутер для обработчиков редактирования
edit_router = Router()

# Set up logging
logger = setup_logger(__name__)

@edit_router.callback_query(F.data.startswith("hint_edit_"))
async def process_hint_edit(callback: CallbackQuery, state: FSMContext):
    """
    Process callback when user wants to edit an existing hint.
    
    Args:
        callback: The callback query from Telegram
        state: The FSM state context
    """
    # Parse callback data
    callback_parts = callback.data.split("_")
    if len(callback_parts) < 4:
        await callback.answer("Ошибка: неверный формат данных")
        return

    hint_type = callback_parts[2]
    word_id = callback_parts[3]
    
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
    
    # Check if word_id matches current word
    current_word_id = current_word.get("id") or current_word.get("_id") or current_word.get("word_id")
    if current_word_id != word_id:
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
    
    # Save to state
    await hint_state.save_to_state(state)
    await state.set_state(HintStates.editing)
    
    # Get word info for display
    word_foreign = current_word.get("word_foreign")
    transcription = current_word.get("transcription", "")
    translation = current_word.get("translation", "")
    
    # Prepare message text - объединяем всё в одно сообщение
    message_text = (
        f"📝 Редактирование подсказки\n\n"
        f"Слово: <b>{word_foreign}</b>\n"
        f"Транскрипция: <b>[{transcription}]</b>\n"
        f"Перевод:\n<b>{translation}</b>\n\n"
    )
    
    if current_hint_text:
        # Добавляем текст подсказки для копирования в то же сообщение
        message_text += (
            f"Подсказка <b>«{hint_name}</b>»\n\n"
            f"<code>{current_hint_text}</code>\n\n"
            f"📋 Нажмите на текст, чтобы скопировать.\n"
            f"Либо отправьте новый текст подсказки.\n\n"
            f"Либо запишите голосовое сообщение.\n"
            f"Для отмены редактирования отправьте /cancel"
        )
    else:
        message_text += (
            f"Отправьте новый текст подсказки.\n"
            f"Либо запишите голосовое сообщение.\n"
            f"Для отмены редактирования отправьте /cancel"
        )
    
    await callback.message.answer(message_text, parse_mode="HTML")
    await callback.answer()

@edit_router.message(HintStates.editing)
async def process_hint_edit_text(message: Message, state: FSMContext):
    """
    Process the edited hint text entered by the user as text or voice message.
    
    Args:
        message: The message object from Telegram
        state: The FSM state context
    """
    # Load hint state from FSM
    hint_state = await HintState.from_state(state)
    
    # Validate hint state
    if not hint_state.is_valid():
        await message.answer("❌ Ошибка: недостаточно данных для редактирования подсказки. Используйте /cancel для отмены.")
        return
    
    # Load user word state for db_user_id and current_word
    user_word_state = await UserWordState.from_state(state)
    
    # Validate user word state
    if not user_word_state.is_valid():
        await message.answer("❌ Ошибка: недостаточно данных о пользователе или слове. Используйте /cancel для отмены.")
        return
    
    # Get hint text from message
    hint_text = None
    
    if message.text:
        # Если получено текстовое сообщение
        hint_text = message.text
    elif message.voice:
        # Если получено голосовое сообщение
        processing_msg = await message.answer("🎙️ Распознаю ваше голосовое сообщение...")
        
        try:
            # Импортируем модуль распознавания речи
            from app.utils.voice_recognition import process_telegram_voice
            
            # Распознаем голосовое сообщение
            recognized_text = await process_telegram_voice(message.bot, message.voice)
            
            if recognized_text:
                hint_text = recognized_text
                # Удаляем сообщение о процессе распознавания
                await processing_msg.delete()
                # Уведомляем о результате
                await message.answer(
                    f"✅ Распознано из голосового сообщения:\n\n"
                    f"<code>{recognized_text}</code>\n\n"
                    f"Сохраняю эту подсказку...",
                    parse_mode="HTML"
                )
            else:
                await processing_msg.delete()
                await message.answer("❌ Не удалось распознать голосовое сообщение. Пожалуйста, отправьте текст или попробуйте еще раз.")
                return
        except Exception as e:
            logger.error(f"Error processing voice message: {e}", exc_info=True)
            await processing_msg.delete()
            await message.answer("❌ Ошибка при распознавании голосового сообщения. Пожалуйста, попробуйте еще раз или отправьте текст.")
            return
    else:
        await message.answer("⚠️ Пожалуйста, отправьте текст или голосовое сообщение")
        return
    
    # Оставшаяся логика сохранения подсказки (существующий код)
    # ...
    
    # Update user word data with hint
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
        return
    
    # Update current word data in state with new hint
    if user_word_state.word_data:
        # If user_word_data exists, update there
        user_word_data = user_word_state.word_data.get("user_word_data", {})
        if not user_word_data:
            user_word_state.word_data["user_word_data"] = {}
            
        user_word_state.word_data["user_word_data"][hint_state.hint_key] = hint_text
        
        # Добавляем подсказку в список использованных, если она еще не там
        used_hints = user_word_state.get_flag("used_hints", [])
        hint_type = hint_state.get_hint_type()
        if hint_type and hint_type not in used_hints:
            used_hints.append(hint_type)
            user_word_state.set_flag("used_hints", used_hints)
        
        # Save updated word data to state
        await user_word_state.save_to_state(state)
    
    # Confirm success with the diff between old and new hint
    old_hint = hint_state.current_hint_text or ""
    if old_hint != hint_text:
        await message.answer(
            f"✅ Подсказка «{hint_state.hint_name}» успешно обновлена!\n\n"
            f"Было:\n<code>{old_hint}</code>\n\n"
            f"Стало:\n<code>{hint_text}</code>\n\n"
            "Продолжаем изучение слов...",
            parse_mode="HTML",
        )
    else:
        await message.answer(
            f"✅ Подсказка «{hint_state.hint_name}» сохранена без изменений.\n\n"
            f"Текст подсказки:\n<code>{hint_text}</code>\n\n"
            "Продолжаем изучение слов...",
            parse_mode="HTML",
        )
    
    # Return to studying state
    await state.set_state(StudyStates.studying)
    await show_study_word(message, state)