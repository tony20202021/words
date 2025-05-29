"""
Handlers for utility word actions during the study process.
Обработчики для утилитарных действий со словами (переключение пропуска и т.д.).
"""

from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext

from app.utils.api_utils import get_api_client_from_bot
from app.utils.logger import setup_logger
from app.utils.error_utils import validate_state_data
from app.utils.state_models import UserWordState
from app.utils.word_data_utils import update_word_score
from app.utils.settings_utils import get_user_language_settings
from app.bot.handlers.study.study_words import show_study_word

# Импортируем централизованные состояния
from app.bot.states.centralized_states import StudyStates

# Создаем роутер для утилитарных действий
utility_router = Router()

logger = setup_logger(__name__)


@utility_router.callback_query(F.data == "toggle_word_skip", StudyStates.studying)
@utility_router.callback_query(F.data == "toggle_word_skip", StudyStates.viewing_word_details)
async def process_toggle_word_skip(callback: CallbackQuery, state: FSMContext):
    """
    Process callback when user wants to toggle the skip flag for the word.
    
    Args:
        callback: The callback query from Telegram
        state: The FSM state context
    """
    user_id = callback.from_user.id
    username = callback.from_user.username
    full_name = callback.from_user.full_name

    logger.info(f"'toggle_word_skip' callback from {full_name} ({username})")
    
    # Validate state data
    is_valid, state_data = await validate_state_data(
        state, 
        ["current_word", "current_word_id", "db_user_id"],
        callback,
        "Ошибка: недостаточно данных для изменения флага пропуска слова"
    )
    
    if not is_valid:
        return
    
    # Get required data
    current_word = state_data["current_word"]
    current_word_id = state_data["current_word_id"]
    db_user_id = state_data["db_user_id"]
    
    # Получаем настройку отображения отладочной информации
    settings = await get_user_language_settings(callback, state)
    show_debug = settings.get("show_debug", False)
    
    # Проверяем текущее состояние флага пропуска
    user_word_data = current_word.get("user_word_data", {})
    current_skip_status = user_word_data.get("is_skipped", False)
    
    # Инвертируем статус пропуска
    new_skip_status = not current_skip_status
    
    try:
        # Update word with new skip status
        success, result = await update_word_score(
            callback.bot,
            db_user_id,
            current_word_id,
            score=0,
            word=current_word,
            message_obj=callback,
            is_skipped=new_skip_status  # Новый статус пропуска
        )
        
        if not success:
            return
        
        # Show word information
        word_foreign = current_word.get("word_foreign")
        transcription = current_word.get("transcription", "")
        
        # Формируем сообщение о смене статуса
        status_message = (
            f"⏩ Статус изменен: слово теперь будет {'пропускаться' if new_skip_status else 'показываться'} в будущем.\n\n"
            f"Слово: <b>{word_foreign}</b>\n"
        )
        
        if transcription:
            status_message += f"Транскрипция: <b>[{transcription}]</b>\n\n"
        
        # Добавляем отладочную информацию, если она включена
        if show_debug:
            status_message += f"🔍 <b>Отладочная информация:</b>\n"
            status_message += f"ID слова: {current_word_id}\n"
            status_message += f"Предыдущий статус пропуска: {current_skip_status}\n"
            status_message += f"Новый статус пропуска: {new_skip_status}\n\n"
        
        await callback.message.answer(
            status_message,
            parse_mode="HTML"
        )
        
        # Обновляем слово в состоянии
        user_word_state = await UserWordState.from_state(state)
        
        if user_word_state.is_valid() and user_word_state.word_data:
            # Обновляем данные о пропуске в локальном состоянии
            if "user_word_data" not in user_word_state.word_data:
                user_word_state.word_data["user_word_data"] = {}
                
            user_word_state.word_data["user_word_data"]["is_skipped"] = new_skip_status
            
            # Логирование данных для отладки
            logger.info(f"Updated word data with new skip status: {new_skip_status}")
            logger.info(f"Word data is_skipped: {user_word_state.word_data.get('user_word_data', {}).get('is_skipped')}")
            
            # Сохраняем обновленное состояние
            await user_word_state.save_to_state(state)
            
            # Get show_hints setting
            from app.utils.settings_utils import get_show_hints_setting
            show_hints = await get_show_hints_setting(callback, state)
            
            # Получаем список использованных подсказок
            used_hints = user_word_state.get_flag("used_hints", [])
            
            # Показываем слово снова с обновленной клавиатурой и флагом пропуска
            await show_study_word(callback.message, state, need_new_message=False)
            
    except Exception as e:
        logger.error(f"Error processing toggle_word_skip: {e}", exc_info=True)
        await callback.message.answer(
            f"❌ Ошибка при обработке флага пропуска слова: {str(e)}"
        )
    
    await callback.answer()
    