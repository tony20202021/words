"""
Handlers for hint toggling.
"""

from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext

from app.utils.api_utils import get_api_client_from_bot
from app.utils.logger import setup_logger
from app.utils.error_utils import validate_state_data
from app.utils.state_models import UserWordState
from app.utils.word_data_utils import get_hint_text, update_word_score
from app.utils.hint_constants import get_hint_key, get_hint_name, get_hint_icon
from app.bot.keyboards.study_keyboards import create_word_keyboard
from app.utils.formatting_utils import format_study_word_message, format_used_hints
from app.utils.settings_utils import get_show_hints_setting

# Создаем вложенный роутер для обработчиков переключения подсказок
toggle_router = Router()

# Set up logging
logger = setup_logger(__name__)

"""
Обновленная функция process_hint_toggle в hint/toggle_handlers.py
"""

@toggle_router.callback_query(F.data.startswith("hint_toggle_"))
async def process_hint_toggle(callback: CallbackQuery, state: FSMContext):
    """
    Process callback when user wants to toggle a hint visibility.
    Updates the current message to show or hide the hint.
    
    Args:
        callback: The callback query from Telegram
        state: The FSM state context
    """
    # Логируем полный callback_data для отладки
    logger.info(f"Received hint toggle callback_data: {callback.data}")
    
    # Разбор callback_data - сейчас этот формат проще:
    # hint_toggle_TYPE_ID где TYPE не содержит подчеркиваний
    parts = callback.data.split('_', 3)
    if len(parts) < 4:
        await callback.answer("Ошибка: неверный формат данных")
        return
    
    # Теперь разбор намного проще
    hint_type = parts[2]
    word_id = parts[3]
    
    logger.info(f"Parsed toggle callback_data: hint_type={hint_type}, word_id={word_id}")
    
    # Validate state data
    is_valid, state_data = await validate_state_data(
        state, 
        ["current_word", "db_user_id"],
        callback,
        "Ошибка: недостаточно данных для отображения подсказки"
    )
    
    if not is_valid:
        return
    
    # Get current word and user ID
    current_word = state_data["current_word"]
    db_user_id = state_data["db_user_id"]
    
    # Проверяем совпадение ID слова
    current_word_id = None
    for id_field in ["id", "_id", "word_id"]:
        if id_field in current_word and current_word[id_field]:
            current_word_id = str(current_word[id_field])
            if current_word_id == word_id:
                break
    
    if not current_word_id or current_word_id != word_id:
        logger.error(f"Word ID mismatch: callback_word_id={word_id}, current_word_id={current_word_id}")
        await callback.answer("Ошибка: несоответствие ID слова")
        return
    
    # Получаем ключ и имя подсказки
    hint_key = get_hint_key(hint_type)
    hint_name = get_hint_name(hint_type)
    hint_icon = get_hint_icon(hint_type)
    
    if not hint_key or not hint_name:
        await callback.answer("Ошибка: неизвестный тип подсказки")
        return
    
    # Получаем текст подсказки
    hint_text = await get_hint_text(
        callback.bot, 
        db_user_id, 
        word_id, 
        hint_key, 
        current_word
    )
    
    if not hint_text:
        logger.error(f"Подсказка не найдена")
        await callback.answer("Подсказка не найдена")
        return
    
    # Получаем текущий список активных подсказок из состояния
    user_word_state = await UserWordState.from_state(state)
    
    # Получаем список использованных подсказок
    used_hints = user_word_state.get_flag("used_hints", []) if user_word_state.is_valid() else []
    
    # Переключаем состояние подсказки
    if hint_type in used_hints:
        logger.error(f"Попытка скрыть подсказку {hint_type}")
    else:
        # Если подсказка не активна, добавляем её и устанавливаем оценку 0
        used_hints.append(hint_type)
        
        # Добавляем подсказку в список использованных
        user_word_state.set_flag("used_hints", used_hints)
        
        # Устанавливаем оценку 0
        await update_word_score(
            callback.bot,
            db_user_id,
            word_id,
            score=0,
            word=current_word,
            message_obj=callback
        )
    
    # Сохраняем обновленный список использованных подсказок
    user_word_state.set_flag("used_hints", used_hints)
    await user_word_state.save_to_state(state)
    
    # Получаем данные для обновления сообщения
    word_shown = user_word_state.get_flag("word_shown", False)
    show_hints = await get_show_hints_setting(callback, state)
    
    # Формируем базовое сообщение
    language_name_ru = ""
    language_name_foreign = ""
    
    # Получаем информацию о языке, если доступна
    language_id = current_word.get("language_id")
    if language_id:
        api_client = get_api_client_from_bot(callback.bot)
        language_response = await api_client.get_language(language_id)
        if language_response["success"] and language_response["result"]:
            language = language_response["result"]
            language_name_ru = language.get("name_ru", "")
            language_name_foreign = language.get("name_foreign", "")
    
    # Получаем детали слова
    word_number = current_word.get("word_number", 0)
    translation = current_word.get("translation", "")
    word_foreign = current_word.get("word_foreign", "")
    transcription = current_word.get("transcription", "")
    
    # Получаем данные пользователя о слове
    user_word_data = current_word.get("user_word_data", {})
    is_skipped = user_word_data.get("is_skipped", False)
    check_interval = user_word_data.get("check_interval", 0)
    next_check_date = user_word_data.get("next_check_date")
    score = user_word_data.get("score", 0)
    
    # Формируем основное сообщение
    message_text = format_study_word_message(
        language_name_ru,
        language_name_foreign,
        word_number,
        translation,
        is_skipped,
        score,
        check_interval,
        next_check_date,
        show_word=word_shown,
        word_foreign=word_foreign,
        transcription=transcription
    )
    
    # Добавляем активные подсказки с помощью новой функции
    hint_text = await format_used_hints(
        bot=callback.bot,
        user_id=db_user_id,
        word_id=word_id,
        current_word=current_word,
        used_hints=used_hints,
        include_header=True
    )
    
    message_text += hint_text
    
    # Создаем клавиатуру с учетом активных подсказок и использованных подсказок
    keyboard = create_word_keyboard(
        current_word, 
        word_shown=word_shown, 
        show_hints=show_hints,
        used_hints=used_hints,
    )
    
    # Обновляем сообщение
    try:
        await callback.message.edit_text(
            message_text,
            reply_markup=keyboard,
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Error updating message with toggled hints: {e}", exc_info=True)
        await callback.message.answer(
            message_text,
            reply_markup=keyboard,
            parse_mode="HTML"
        )
