"""
Refactored handlers for hint toggling.
Now uses centralized utilities and constants.
"""

from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext

from app.utils.logger import setup_logger
from app.utils.error_utils import validate_state_data
from app.utils.state_models import UserWordState
from app.utils.word_data_utils import get_hint_text, update_word_score
from app.utils.hint_constants import get_hint_key, get_hint_name, get_hint_icon
from app.bot.handlers.study.study_words import show_study_word

# Import callback utilities
from app.utils.callback_constants import CallbackParser

# Импортируем централизованные состояния
from app.bot.states.centralized_states import StudyStates, HintStates

# Создаем вложенный роутер для обработчиков переключения подсказок
toggle_router = Router()

# Set up logging
logger = setup_logger(__name__)


@toggle_router.callback_query(F.data.startswith("hint_toggle_"), StudyStates.studying)
@toggle_router.callback_query(F.data.startswith("hint_toggle_"), StudyStates.viewing_word_details)
async def process_hint_toggle(callback: CallbackQuery, state: FSMContext):
    """
    Process callback when user wants to toggle a hint visibility.
    Updates the current message to show or hide the hint.
    Now uses improved callback parsing and FSM states.
    
    Args:
        callback: The callback query from Telegram
        state: The FSM state context
    """
    logger.info(f"Received hint toggle callback: {callback.data}")
    
    # Parse callback data using the new parser
    parsed = CallbackParser.parse_hint_action(callback.data)
    if not parsed:
        logger.error(f"Could not parse callback_data: {callback.data}")
        await callback.answer("Ошибка формата данных")
        return
    
    action, hint_type, word_id = parsed
    logger.info(f"Parsed toggle callback: hint_type={hint_type}, word_id={word_id}")
    
    # Validate state data
    is_valid, state_data = await validate_state_data(
        state, 
        ["word_data", "db_user_id"],
        callback,
        "Ошибка: недостаточно данных для отображения подсказки"
    )
    
    if not is_valid:
        return
    
    # Get current word and user ID
    current_word = state_data["word_data"]
    db_user_id = state_data["db_user_id"]
    
    # Verify word ID matches current word
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
    
    # Get hint key and name
    hint_key = get_hint_key(hint_type)
    hint_name = get_hint_name(hint_type)
    hint_icon = get_hint_icon(hint_type)
    
    if not hint_key or not hint_name:
        await callback.answer("Ошибка: неизвестный тип подсказки")
        return
    
    # Get hint text
    hint_text = await get_hint_text(
        callback.bot, 
        db_user_id, 
        word_id, 
        hint_key, 
        current_word
    )
    
    if not hint_text:
        logger.error("Hint text not found")
        await callback.answer("Подсказка не найдена")
        return
    
    # Get current user word state
    user_word_state = await UserWordState.from_state(state)
    
    # Get list of used hints
    used_hints = user_word_state.get_flag("used_hints", []) if user_word_state.is_valid() else []
    
    # Toggle hint state - add hint to used hints and set score to 0
    if hint_type not in used_hints:
        used_hints.append(hint_type)
        
        # Update user word state
        user_word_state.set_flag("used_hints", used_hints)
        
    # Set score to 0 for using hint
    await update_word_score(
        callback.bot,
        db_user_id,
        word_id,
        score=0,
        word=current_word,
        message_obj=callback
    )
        
    # Save updated used hints
    await user_word_state.save_to_state(state)
    
    await show_study_word(callback, state, user_word_state, need_new_message=False)
