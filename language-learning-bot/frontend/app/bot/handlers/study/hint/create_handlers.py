"""
Handlers for hint creation.
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
from app.bot.handlers.study.study_states import HintStates, StudyStates
from app.bot.handlers.study.study_words import show_study_word

# Создаем вложенный роутер для обработчиков создания подсказок
create_router = Router()

# Set up logging
logger = setup_logger(__name__)

@create_router.callback_query(F.data.startswith("hint_create_"))
async def process_hint_create(callback: CallbackQuery, state: FSMContext):
    """
    Process callback when user wants to create a new hint.
    
    Args:
        callback: The callback query from Telegram
        state: The FSM state context
    """
    # Логируем полный callback_data для отладки
    logger.info(f"Received callback_data: {callback.data}")
    
    # Сначала выделяем два первых компонента (hint_create)
    prefixes = callback.data.split('_', 2)
    if len(prefixes) < 3:
        await callback.answer("Ошибка: неверный формат данных")
        return
    
    # Теперь разбираем остальную часть строки
    remainder = prefixes[2]  # "phonetic_association_ID" или "meaning_ID"
    
    # Проверяем, какой тип подсказки содержится в remainder
    hint_type = None
    word_id = None
    
    # Проверка для каждого возможного типа подсказки
    for possible_type in get_all_hint_types():
        print(possible_type, prefixes)
        if remainder.startswith(possible_type + "_"):
            hint_type = possible_type
            word_id = remainder[len(possible_type) + 1:]  # Всё после "TYPE_"
            break
    
    if not hint_type or not word_id:
        logger.error(f"Could not parse callback_data: {callback.data}")
        await callback.answer("Ошибка формата данных подсказки")
        return
    
    logger.info(f"Parsed callback_data: action=create, hint_type={hint_type}, word_id={word_id}")
    
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
    
    # Check if word_id matches current word
    current_word_id = None
    for id_field in ["id", "_id", "word_id"]:
        if id_field in current_word and current_word[id_field]:
            current_word_id = str(current_word[id_field])
            # Если найдено совпадение, прерываем проверку
            if current_word_id == word_id:
                break
    
    # Логирование для отладки
    logger.info(f"Comparing word IDs: callback_word_id={word_id}, current_word_id={current_word_id}")
    logger.info(f"Current word fields: {[k for k in current_word.keys() if k in ['id', '_id', 'word_id']]}")
    
    if not current_word_id or current_word_id != word_id:
        # Логируем ошибку с более подробной информацией
        logger.error(f"Word ID mismatch: callback_word_id={word_id}, available IDs in current_word: "
                    f"id={current_word.get('id')}, _id={current_word.get('_id')}, word_id={current_word.get('word_id')}")
        
        # Отправляем ошибку через alert, а не просто сообщение
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
    
    # Save to state
    await hint_state.save_to_state(state)
    await state.set_state(HintStates.creating)
    
    # Get word info for display
    word_foreign = current_word.get("word_foreign")
    transcription = current_word.get("transcription", "")
    translation = current_word.get("translation", "")
    
    # Ask for hint text
    await callback.message.answer(
        f"Слово: <code>{word_foreign}</code>\n\n"
        f"Транскрипция: <b>[{transcription}]</b>\n\n"
        f"Перевод:\n<b>{translation}</b>\n\n"
        f"📝 Создание подсказки типа «{hint_name}»\n\n"
        f"Пожалуйста, введите текст подсказки,\n"
        f"или запишите голосовое сообщение,\n"
        f"или отправьте /cancel для отмены:",
        parse_mode="HTML",
    )
    
    await callback.answer()

@create_router.message(HintStates.creating)
async def process_hint_text(message: Message, state: FSMContext):
    """
    Process the hint text entered by the user as text or voice message.
    
    Args:
        message: The message object from Telegram
        state: The FSM state context
    """
    # Load hint state from FSM
    hint_state = await HintState.from_state(state)
    
    # Validate hint state
    if not hint_state.is_valid():
        await message.answer("❌ Ошибка: недостаточно данных для создания подсказки. Используйте /cancel для отмены.")
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

        # Стандартное сообщение успеха для текстовой подсказки
        await message.answer(
            f"✅ Подсказка успешно создана!\n\n"
            f"«{hint_state.hint_name}»\n\n"
            f"Текст подсказки:\n<code>{hint_text}</code>\n\n"
            "Продолжаем изучение слов...",
            parse_mode="HTML",
        )
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
                    f"✅ Подсказка успешно распознана из голосового сообщения!\n\n"
                    f"«{hint_state.hint_name}»\n\n"
                    f"Текст подсказки:\n<code>{recognized_text}</code>\n\n"
                    "Продолжаем изучение слов...",
                    parse_mode="HTML",
                )
            else:
                await processing_msg.delete()
                await message.answer("❌ Не удалось распознать голосовое сообщение. Пожалуйста, отправьте текст или попробуйте еще раз.")
                return
        except ImportError:
            logger.error("Voice recognition module not available")
            await processing_msg.delete()
            await message.answer("❌ Распознавание речи недоступно. Пожалуйста, отправьте текст.")
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
        
        # Добавляем подсказку в список использованных
        used_hints = user_word_state.get_flag("used_hints", [])
        hint_type = hint_state.get_hint_type()
        if hint_type and hint_type not in used_hints:
            used_hints.append(hint_type)
            user_word_state.set_flag("used_hints", used_hints)
        
        # Добавляем подсказку в список активных подсказок, чтобы она сразу отображалась 
        # на экране изучения слова
        active_hints = user_word_state.get_flag("active_hints", [])
        if hint_type and hint_type not in active_hints:
            active_hints.append(hint_type)
            user_word_state.set_flag("active_hints", active_hints)
                    # Save updated word data to state
        await user_word_state.save_to_state(state)
        
    # Return to studying state
    await state.set_state(StudyStates.studying)
    await show_study_word(message, state)

@create_router.callback_query(F.data.startswith("edit_recognized_"))
async def process_edit_recognized(callback: CallbackQuery, state: FSMContext):
    """
    Обработчик для быстрого перехода к редактированию распознанного текста.
    
    Args:
        callback: The callback query from Telegram
        state: The FSM state context
    """
    # Парсим callback_data: edit_recognized_TYPE_ID
    parts = callback.data.split('_', 2)
    if len(parts) < 3:
        await callback.answer("Ошибка в формате запроса")
        return
    
    # Получаем параметры из частей callback_data
    remainder = parts[2]  # "TYPE_ID"
    
    # Найдем разделитель между типом и ID
    for possible_type in get_all_hint_types():
        if remainder.startswith(possible_type + "_"):
            hint_type = possible_type
            word_id = remainder[len(possible_type) + 1:]  # Всё после "TYPE_"
            break
    else:
        await callback.answer("Ошибка: не удалось определить тип подсказки")
        return
    
    # Проверяем состояние
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
    
    # Получаем ключ и имя подсказки
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
    
    # Prepare message text for editing
    await callback.message.edit_text(
        f"📝 Редактирование распознанного текста\n\n"
        f"Слово: <b>{word_foreign}</b>\n"
        f"Транскрипция: <b>[{transcription}]</b>\n"
        f"Перевод:\n<b>{translation}</b>\n\n"
        f"Подсказка <b>«{hint_name}»</b>\n\n"
        f"<code>{current_hint_text}</code>\n\n"
        f"📋 Нажмите на текст, чтобы скопировать.\n"
        f"Отправьте исправленный текст или используйте /cancel для отмены.",
        parse_mode="HTML"
    )
    
    await callback.answer()
    