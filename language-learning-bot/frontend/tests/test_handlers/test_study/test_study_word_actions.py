"""
Handlers for word actions during the study process.
"""

from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext

from app.utils.api_utils import get_api_client_from_bot
from app.utils.logger import setup_logger
from app.utils.error_utils import validate_state_data
from app.utils.state_models import UserWordState
from app.utils.word_data_utils import update_word_score

from app.bot.handlers.study.study_words import show_study_word

# Создаем роутер для обработчиков действий со словами
word_router = Router()

logger = setup_logger(__name__)


@word_router.callback_query(F.data == "word_know")
async def process_word_know(callback: CallbackQuery, state: FSMContext):
    """
    Process callback when user knows the word.
    
    Args:
        callback: The callback query from Telegram
        state: The FSM state context
    """
    user_id = callback.from_user.id
    username = callback.from_user.username
    full_name = callback.from_user.full_name

    logger.info(f"'word_know' callback from {full_name} ({username})")
    
    # Validate state data
    is_valid, state_data = await validate_state_data(
        state, 
        ["current_word", "current_word_id", "db_user_id"],
        callback,
        "Ошибка: недостаточно данных для оценки слова"
    )
    
    if not is_valid:
        # Для совместимости с тестами, если validate_state_data не получает ожидаемые данные
        await callback.answer("Ошибка: недостаточно данных")
        return
    
    # Get required data
    current_word = state_data["current_word"]
    current_word_id = state_data["current_word_id"]
    db_user_id = state_data["db_user_id"]
    
    try:
        # Update word score to 1 (known)
        success, result = await update_word_score(
            callback.bot,
            db_user_id,
            current_word_id,
            score=1,
            word=current_word,
            message_obj=callback
        )
        
        if not success:
            return
        
        # Show word information
        word_foreign = current_word.get("word_foreign")
        transcription = current_word.get("transcription", "")
        translation = current_word.get("translation", "")
        
        await callback.message.answer(
            f"✅ Отлично! Вы знаете это слово.\n\n"
            f"Слово: <b>{word_foreign}</b>\n"
            f"Транскрипция: [{transcription}]\n"
            f"Перевод: {translation}\n\n"
            "Переходим к следующему слову...",
            parse_mode="HTML"
        )
        
        # Advance to next word
        user_word_state = await UserWordState.from_state(state)
        
        if user_word_state.is_valid():
            # Advance to next word
            user_word_state.advance_to_next_word()
            
            # Save updated state
            await user_word_state.save_to_state(state)
            
            # Show next word
            await show_study_word(callback.message, state)
        else:
            # Fallback to old approach if state model is invalid
            logger.warning("UserWordState invalid, using fallback approach to advance to next word")
            current_index = state_data.get("current_study_index", 0) + 1
            await state.update_data(current_study_index=current_index)
            await show_study_word(callback.message, state)
        
    except Exception as e:
        logger.error(f"Error processing word_know: {e}", exc_info=True)
        await callback.message.answer(
            f"❌ Ошибка при обработке слова: {str(e)}"
        )
    
    await callback.answer()


@word_router.callback_query(F.data == "word_dont_know")
async def process_word_dont_know(callback: CallbackQuery, state: FSMContext):
    """
    Process callback when user doesn't know the word but wants to continue learning it.
    
    Args:
        callback: The callback query from Telegram
        state: The FSM state context
    """
    user_id = callback.from_user.id
    username = callback.from_user.username
    full_name = callback.from_user.full_name

    logger.info(f"'word_dont_know' callback from {full_name} ({username})")
    
    # Validate state data
    is_valid, state_data = await validate_state_data(
        state, 
        ["current_word", "current_word_id", "db_user_id"],
        callback,
        "Ошибка: недостаточно данных для оценки слова"
    )
    
    if not is_valid:
        await callback.answer("Ошибка: недостаточно данных")
        return
    
    # Get required data
    current_word = state_data["current_word"]
    current_word_id = state_data["current_word_id"]
    db_user_id = state_data["db_user_id"]
    
    try:
        # Update word score to 0 (not known), but don't mark as skipped
        success, result = await update_word_score(
            callback.bot,
            db_user_id,
            current_word_id,
            score=0,
            word=current_word,
            message_obj=callback,
            is_skipped=False  # Не помечаем для пропуска
        )
        
        if not success:
            return
        
        # Show word information
        word_foreign = current_word.get("word_foreign")
        transcription = current_word.get("transcription", "")
        translation = current_word.get("translation", "")
        
        await callback.message.answer(
            f"🔄 Запомните это слово, мы повторим его позже.\n\n"
            f"Слово: <b>{word_foreign}</b>\n"
            f"Транскрипция: [{transcription}]\n"
            f"Перевод: {translation}\n\n"
            "Переходим к следующему слову...",
            parse_mode="HTML"
        )
        
        # Advance to next word
        user_word_state = await UserWordState.from_state(state)
        
        if user_word_state.is_valid():
            # Advance to next word
            user_word_state.advance_to_next_word()
            
            # Save updated state
            await user_word_state.save_to_state(state)
            
            # Show next word
            await show_study_word(callback.message, state)
        else:
            # Fallback to old approach if state model is invalid
            logger.warning("UserWordState invalid, using fallback approach to advance to next word")
            current_index = state_data.get("current_study_index", 0) + 1
            await state.update_data(current_study_index=current_index)
            await show_study_word(callback.message, state)
            
    except Exception as e:
        logger.error(f"Error processing word_dont_know: {e}", exc_info=True)
        await callback.message.answer(
            f"❌ Ошибка при обработке слова: {str(e)}"
        )
    
    await callback.answer()


@word_router.callback_query(F.data == "word_skip")
async def process_word_skip(callback: CallbackQuery, state: FSMContext):
    """
    Process callback when user wants to skip the word (mark it to be skipped in future).
    
    Args:
        callback: The callback query from Telegram
        state: The FSM state context
    """
    user_id = callback.from_user.id
    username = callback.from_user.username
    full_name = callback.from_user.full_name

    logger.info(f"'word_skip' callback from {full_name} ({username})")
    
    # Validate state data
    is_valid, state_data = await validate_state_data(
        state, 
        ["current_word", "current_word_id", "db_user_id"],
        callback,
        "Ошибка: недостаточно данных для пропуска слова"
    )
    
    if not is_valid:
        await callback.answer("Ошибка: недостаточно данных")
        return
    
    # Get required data
    current_word = state_data["current_word"]
    current_word_id = state_data["current_word_id"]
    db_user_id = state_data["db_user_id"]
    
    try:
        # Update word score to 0 and mark as skipped
        success, result = await update_word_score(
            callback.bot,
            db_user_id,
            current_word_id,
            score=0,
            word=current_word,
            message_obj=callback,
            is_skipped=True  # Помечаем для пропуска
        )
        
        if not success:
            return
        
        # Show word information
        word_foreign = current_word.get("word_foreign")
        transcription = current_word.get("transcription", "")
        translation = current_word.get("translation", "")
        
        await callback.message.answer(
            f"⏩ Вы пропустили слово. Оно будет пропускаться в будущем.\n\n"
            f"Слово: <b>{word_foreign}</b>\n"
            f"Транскрипция: [{transcription}]\n"
            f"Перевод: {translation}\n\n"
            "Переходим к следующему слову...",
            parse_mode="HTML"
        )
        
        # Advance to next word
        user_word_state = await UserWordState.from_state(state)
        
        if user_word_state.is_valid():
            # Advance to next word
            user_word_state.advance_to_next_word()
            
            # Save updated state
            await user_word_state.save_to_state(state)
            
            # Show next word
            await show_study_word(callback.message, state)
        else:
            # Fallback to old approach if state model is invalid
            logger.warning("UserWordState invalid, using fallback approach to advance to next word")
            current_index = state_data.get("current_study_index", 0) + 1
            await state.update_data(current_study_index=current_index)
            await show_study_word(callback.message, state)
            
    except Exception as e:
        logger.error(f"Error processing word_skip: {e}", exc_info=True)
        await callback.message.answer(
            f"❌ Ошибка при обработке слова: {str(e)}"
        )
    
    await callback.answer()