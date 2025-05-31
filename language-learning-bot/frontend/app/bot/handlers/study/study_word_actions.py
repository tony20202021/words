"""
Study word actions handlers for Language Learning Bot.
Handles word evaluation and navigation during study process.
FIXED: Proper imports, removed code duplication, improved architecture.
UPDATED: Added word image display functionality.
UPDATED: Added admin edit from study functionality.
"""

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message, BufferedInputFile
from aiogram.fsm.context import FSMContext

from app.utils.api_utils import get_api_client_from_bot
from app.utils.logger import setup_logger
from app.utils.word_data_utils import update_word_score, ensure_user_word_data
from app.utils.state_models import UserWordState
from app.utils.hint_settings_utils import get_individual_hint_settings
from app.utils.settings_utils import get_show_debug_setting
from app.utils.formatting_utils import format_study_word_message, format_used_hints
from app.utils.word_image_generator import generate_word_image
from app.utils.admin_utils import is_user_admin  # НОВОЕ: Импорт утилиты для проверки админа
from app.bot.keyboards.study_keyboards import create_adaptive_study_keyboard, create_word_image_keyboard
from app.bot.handlers.study.study_words import show_study_word, load_next_batch
from app.bot.states.centralized_states import StudyStates, AdminStates  # НОВОЕ: Импорт AdminStates
from app.utils.callback_constants import CallbackData, CallbackParser, format_admin_edit_from_study_callback

# Создаем роутер для действий со словами
word_actions_router = Router()

logger = setup_logger(__name__)


@word_actions_router.message(Command("show_big"))
async def cmd_show_big_word(message: Message, state: FSMContext):
    """
    Обработчик команды /show_big для показа увеличенного слова.
    
    Args:
        message: The message object
        state: FSM context
    """
    logger.info(f"'/show_big' command from {message.from_user.full_name}")
    
    # Get current word state
    user_word_state = await UserWordState.from_state(state)
    
    if not user_word_state.is_valid() or not user_word_state.has_more_words():
        await message.answer("❌ Нет активного слова для увеличения")
        return
    
    # Get current word
    current_word = user_word_state.get_current_word()
    if not current_word:
        await message.answer("❌ Ошибка получения текущего слова")
        return
    
    # Show word image using common function
    await _show_word_image(message, state, current_word)

@word_actions_router.callback_query(F.data == CallbackData.SHOW_WORD_IMAGE)
async def process_show_word_image_callback(callback: CallbackQuery, state: FSMContext):
    """
    Обработчик callback для показа увеличенного слова.
    
    Args:
        callback: The callback query
        state: FSM context
    """
    logger.info(f"'show_word_image' callback from {callback.from_user.full_name}")
    
    # Get current word state
    user_word_state = await UserWordState.from_state(state)
    
    if not user_word_state.is_valid() or not user_word_state.has_more_words():
        await callback.answer("❌ Нет активного слова для увеличения")
        return
    
    # Get current word
    current_word = user_word_state.get_current_word()
    if not current_word:
        await callback.answer("❌ Ошибка получения текущего слова")
        return
    
    # Show word image using common function
    await _show_word_image(callback, state, current_word)
    await callback.answer("🔍 Показываю крупное написание")

@word_actions_router.callback_query(F.data == CallbackData.BACK_FROM_IMAGE, StudyStates.viewing_word_image)
async def process_back_from_image(callback: CallbackQuery, state: FSMContext):
    """
    Обработчик возврата от изображения к экрану изучения.
    
    Args:
        callback: The callback query
        state: FSM context
    """
    logger.info(f"'back_from_image' callback from {callback.from_user.full_name}")
    
    # Get current word state
    user_word_state = await UserWordState.from_state(state)
    
    if not user_word_state.is_valid():
        await callback.answer("❌ Ошибка состояния изучения")
        return
    
    # Determine which state to return to
    word_shown = user_word_state.get_flag("word_shown", False)
    if word_shown:
        await state.set_state(StudyStates.viewing_word_details)
    else:
        await state.set_state(StudyStates.studying)
    
    # Show study word again (without creating new message)
    await show_study_word(callback, state, user_word_state, need_new_message=True)
    await callback.answer("⬅️ Возвращаемся к изучению")

# НОВОЕ: Обработчик для возврата к изучению из админ-режима
@word_actions_router.callback_query(F.data == CallbackData.BACK_TO_STUDY_FROM_ADMIN)
async def process_back_to_study_from_admin(callback: CallbackQuery, state: FSMContext):
    """
    Обработчик возврата к изучению слов из админ-режима редактирования.
    
    Args:
        callback: The callback query
        state: FSM context
    """
    logger.info(f"'back_to_study_from_admin' callback from {callback.from_user.full_name}")
    
    # # Получаем сохраненный контекст изучения
    # admin_state_data = await state.get_data()
    # study_state_data = admin_state_data.get("study_state_data", {})
    # previous_study_state = admin_state_data.get("previous_study_state")
    
    # if not study_state_data:
    #     logger.warning("No study context found, redirecting to study command")
    #     await callback.answer("⚠️ Контекст изучения потерян, перезапускаем изучение")
        
    #     # Импортируем и вызываем команду изучения
    #     from app.bot.handlers.study.study_commands import cmd_study
        
    #     # Создаем объект, совместимый с Message для cmd_study
    #     class CallbackAsMessage:
    #         def __init__(self, callback_query):
    #             self.from_user = callback_query.from_user
    #             self.bot = callback_query.bot
                
    #         async def answer(self, text, **kwargs):
    #             await callback_query.message.answer(text, **kwargs)
        
    #     message_like = CallbackAsMessage(callback)
    #     await cmd_study(message_like, state)
    #     await callback.answer()
    #     return
    
    # # Восстанавливаем состояние изучения
    # await state.clear()
    # await state.set_data(study_state_data)
    
    # # Восстанавливаем FSM состояние
    # if previous_study_state:
    #     await state.set_state(previous_study_state)
    # else:
    #     await state.set_state(StudyStates.studying)
    
    # logger.info(f"Restored study state: {previous_study_state}")
    
    await state.set_state(StudyStates.studying)
    
    # Показываем текущее слово изучения
    user_word_state = await UserWordState.from_state(state)
    
    if user_word_state.is_valid():
        await show_study_word(callback, state, user_word_state, need_new_message=True)
        await callback.answer("⬅️ Возвращаемся к изучению")
    else:
        logger.error("Invalid study state after restoration")
        await callback.answer("❌ Ошибка восстановления состояния изучения")
        await callback.message.answer(
            "❌ Ошибка восстановления состояния изучения.\n"
            "Используйте команду /study для начала изучения заново."
        )


async def _show_word_image(
    message_or_callback, 
    state: FSMContext, 
    current_word: dict,
):
    """
    Общая функция для показа изображения слова.
    
    Args:
        message_or_callback: Message or CallbackQuery object
        state: FSM context
        current_word: Current word data
    """
    try:
        # Extract word and transcription
        word_foreign = current_word.get("word_foreign", "")
        transcription = current_word.get("transcription", "")
        
        if not word_foreign:
            error_msg = "❌ Слово на иностранном языке не найдено"
            if hasattr(message_or_callback, 'answer'):
                await message_or_callback.answer(error_msg)
            else:
                await message_or_callback.message.answer(error_msg)
            return
        
        
        # Generate word image
        logger.info(f"Generating image for word: '{word_foreign}', transcription: '{transcription}'")
        
        image_buffer = await generate_word_image(
            word=word_foreign,
            transcription=transcription,
        )
        
        # Create BufferedInputFile from BytesIO for Telegram
        image_buffer.seek(0)  # Reset buffer position
        input_file = BufferedInputFile(
            file=image_buffer.read(),
            filename=f"word_{word_foreign}.png"
        )
        
        # Prepare caption
        caption = ""
        
        # Create keyboard
        keyboard = create_word_image_keyboard()
        
        # Set state
        await state.set_state(StudyStates.viewing_word_image)
        
        # Send image
        if hasattr(message_or_callback, 'answer_photo'):
            # This is a Message object
            await message_or_callback.answer_photo(
                photo=input_file,
                caption=caption,
                reply_markup=keyboard,
                parse_mode="HTML"
            )
        else:
            # This is a CallbackQuery object
            await message_or_callback.message.answer_photo(
                photo=input_file,
                caption=caption,
                reply_markup=keyboard,
                parse_mode="HTML"
            )
        
        logger.info(f"Successfully sent word image for: {word_foreign}")
        
    except Exception as e:
        logger.error(f"Error showing word image: {e}", exc_info=True)
        
        error_msg = "❌ Ошибка при создании изображения слова"
        if hasattr(message_or_callback, 'answer'):
            await message_or_callback.answer(error_msg)
        else:
            await message_or_callback.message.answer(error_msg)
    
@word_actions_router.callback_query(F.data == CallbackData.WORD_KNOW, StudyStates.studying)
async def process_word_know(callback: CallbackQuery, state: FSMContext):
    """
    Process 'I know this word' action.
    FIXED: Uses centralized utilities and proper error handling.
    
    Args:
        callback: The callback query
        state: FSM context
    """
    logger.info(f"'word_know' action from {callback.from_user.full_name}")
    
    # Get current word state
    user_word_state = await UserWordState.from_state(state)
    data = await state.get_data()
    logger.info(f"data {data}")
    
    if not user_word_state.is_valid() or not user_word_state.has_more_words():
        await callback.answer("❌ Нет активного слова для оценки")
        return
    
    # Get current word
    current_word = user_word_state.get_current_word()
    if not current_word:
        await callback.answer("❌ Ошибка получения текущего слова")
        return
    
    # Update word score using centralized utility
    success, result = await update_word_score(
        bot=callback.bot,
        user_id=user_word_state.user_id,
        word_id=user_word_state.word_id,
        score=1,  # Known word
        word=current_word,
        message_obj=callback
    )
    
    if not success:
        await callback.answer("❌ Ошибка обновления оценки слова")
        return
    
    # Update local word data
    if "user_word_data" not in current_word:
        current_word["user_word_data"] = {}
    current_word["user_word_data"].update(result or {})
    current_word["user_word_data"]["score"] = 1
    
    # Mark word as processed and set flags
    user_word_state.mark_word_as_processed()
    user_word_state.set_flag("word_shown", True)
    user_word_state.set_flag("pending_next_word", True)
    user_word_state.set_flag("pending_word_know", True)
    
    # Save state and transition
    await user_word_state.save_to_state(state)
    await state.set_state(StudyStates.confirming_word_knowledge)
    
    # Show word result
    await show_study_word(callback, state, user_word_state, need_new_message=False)
    
    await callback.answer("✅ Отлично! Слово отмечено как известное")

@word_actions_router.callback_query(F.data == CallbackData.WORD_DONT_KNOW, StudyStates.studying)
async def process_word_dont_know(callback: CallbackQuery, state: FSMContext):
    """
    Process 'I don't know this word' action.
    FIXED: Uses centralized utilities and proper error handling.
    
    Args:
        callback: The callback query
        state: FSM context
    """
    logger.info(f"'word_dont_know' action from {callback.from_user.full_name}")
    
    # Get current word state
    user_word_state = await UserWordState.from_state(state)
    
    if not user_word_state.is_valid() or not user_word_state.has_more_words():
        await callback.answer("❌ Нет активного слова для оценки")
        return
    
    # Get current word
    current_word = user_word_state.get_current_word()
    if not current_word:
        await callback.answer("❌ Ошибка получения текущего слова")
        return
    
    # Update word score using centralized utility
    success, result = await update_word_score(
        bot=callback.bot,
        user_id=user_word_state.user_id,
        word_id=user_word_state.word_id,
        score=0,  # Unknown word
        word=current_word,
        message_obj=callback
    )
    
    if not success:
        await callback.answer("❌ Ошибка обновления оценки слова")
        return
    
    # Update local word data
    if "user_word_data" not in current_word:
        current_word["user_word_data"] = {}

    current_word["user_word_data"].update(result or {})
    current_word["user_word_data"]["score"] = 0
    
    # Mark word as processed and set flags
    user_word_state.set_current_word(current_word)
    user_word_state.mark_word_as_processed()
    user_word_state.set_flag("word_shown", True)
    user_word_state.set_flag("pending_next_word", True)
    user_word_state.set_flag("pending_word_know", False)
    
    # Save state and transition
    await user_word_state.save_to_state(state)
    await state.set_state(StudyStates.viewing_word_details)
    
    # Show word result
    await _show_word_result(callback, state, user_word_state, current_word, known=False)
    
    await callback.answer("📝 Слово отмечено как неизвестное")

@word_actions_router.callback_query(F.data == CallbackData.SHOW_WORD, StudyStates.studying)
@word_actions_router.callback_query(F.data == CallbackData.SHOW_WORD, StudyStates.confirming_word_knowledge)
async def process_show_word(callback: CallbackQuery, state: FSMContext):
    """
    Process 'Show word' action.
    
    Args:
        callback: The callback query
        state: FSM context
    """
    logger.info(f"'show_word' 2 action from {callback.from_user.full_name}")
    
    # Get current word state
    user_word_state = await UserWordState.from_state(state)
    
    if not user_word_state.is_valid() or not user_word_state.has_more_words():
        await callback.answer("❌ Нет активного слова для показа")
        return
    
    # Get current word
    current_word = user_word_state.get_current_word()
    if not current_word:
        await callback.answer("❌ Ошибка получения текущего слова")
        return
    
    # Update word score using centralized utility
    success, result = await update_word_score(
        bot=callback.bot,
        user_id=user_word_state.user_id,
        word_id=user_word_state.word_id,
        score=0,  # Unknown word
        word=current_word,
        message_obj=callback
    )
    
    if not success:
        await callback.answer("❌ Ошибка обновления оценки слова")
        return

    # Update local word data
    if "user_word_data" not in current_word:
        current_word["user_word_data"] = {}

    current_word["user_word_data"].update(result or {})
    current_word["user_word_data"]["score"] = 0
    
    # Mark word as processed and set flags
    user_word_state.set_current_word(current_word)
    user_word_state.set_flag("word_shown", True)
    
    # Save state and transition
    await user_word_state.save_to_state(state)
    await state.set_state(StudyStates.viewing_word_details)
    
    # Use centralized display function
    await show_study_word(callback, state, user_word_state, need_new_message=False)
    
    await callback.answer("👁️ Показываю слово")

@word_actions_router.callback_query(F.data == CallbackData.NEXT_WORD)
async def process_next_word(callback: CallbackQuery, state: FSMContext):
    """
    Process 'Next word' action.
    FIXED: Improved batch loading logic and error handling.
    
    Args:
        callback: The callback query
        state: FSM context
    """
    logger.info(f"'next_word' action from {callback.from_user.full_name}")
    
    # Get current word state
    user_word_state = await UserWordState.from_state(state)
    
    if not user_word_state.is_valid():
        await callback.answer("❌ Неверное состояние изучения")
        return
    
    # Try to advance to next word
    if user_word_state.advance_to_next_word():
        # Successfully moved to next word
        await user_word_state.save_to_state(state)
        await state.set_state(StudyStates.studying)
        
        # Show next word using centralized function
        await show_study_word(callback, state, user_word_state, need_new_message=True)
        await callback.answer()
        
    else:
        # No more words in current batch, try to load next batch
        await _handle_batch_completion(callback, state, user_word_state)

@word_actions_router.callback_query(F.data == CallbackData.CONFIRM_NEXT_WORD, StudyStates.confirming_word_knowledge)
async def process_confirm_next_word(callback: CallbackQuery, state: FSMContext):
    """
    Process confirmation to move to next word.
    
    Args:
        callback: The callback query
        state: FSM context
    """
    logger.info(f"'confirm_next_word' action from {callback.from_user.full_name}")
    
    # Simply call next word handler
    await process_next_word(callback, state)

@word_actions_router.callback_query(F.data == CallbackData.TOGGLE_WORD_SKIP)
async def process_toggle_word_skip(callback: CallbackQuery, state: FSMContext):
    """
    Process toggle word skip status.
    FIXED: Uses centralized utilities for data updates.
    
    Args:
        callback: The callback query
        state: FSM context
    """
    logger.info(f"'toggle_word_skip' action from {callback.from_user.full_name}")
    
    # Get current word state
    user_word_state = await UserWordState.from_state(state)
    
    if not user_word_state.is_valid() or not user_word_state.has_more_words():
        await callback.answer("❌ Нет активного слова")
        return
    
    # Get current word
    current_word = user_word_state.get_current_word()
    if not current_word:
        await callback.answer("❌ Ошибка получения текущего слова")
        return
    
    # Toggle skip status
    user_word_data = current_word.get("user_word_data", {})
    current_skip_status = user_word_data.get("is_skipped", False)
    new_skip_status = not current_skip_status
    
    # Update word data using centralized utility
    try:
        update_data = {"is_skipped": new_skip_status}
        success, result = await ensure_user_word_data(
            bot=callback.bot,
            user_id=user_word_state.user_id,
            word_id=user_word_state.word_id,
            update_data=update_data,
            word=current_word,
            message_obj=callback
        )
        
        if success:
            # Update local word data
            if "user_word_data" not in current_word:
                current_word["user_word_data"] = {}
            current_word["user_word_data"]["is_skipped"] = new_skip_status
            
            # Save state
            await user_word_state.save_to_state(state)
            
            # Refresh display using centralized function
            await show_study_word(callback, state, user_word_state, need_new_message=False)
            
            status_text = "пропускать" if new_skip_status else "показывать"
            await callback.answer(f"✅ Слово будет {status_text}")
            
        else:
            await callback.answer("❌ Ошибка изменения статуса слова")
            
    except Exception as e:
        logger.error(f"Error toggling word skip status: {e}")
        await callback.answer("❌ Ошибка изменения статуса слова")

# ИСПРАВЛЕНО: Централизованные вспомогательные функции
async def _show_word_result(
    callback: CallbackQuery, 
    state: FSMContext, 
    user_word_state: UserWordState, 
    current_word: dict, 
    known: bool
):
    """
    Show word result after evaluation using centralized utilities.
    FIXED: Removed code duplication, uses proper hint settings.
    
    Args:
        callback: The callback query
        state: FSM context
        user_word_state: Current word state
        current_word: Current word data
        known: Whether word was marked as known
    """
    try:
        # Get individual hint settings using proper import
        hint_settings = await get_individual_hint_settings(callback, state)
        show_debug = await get_show_debug_setting(callback, state)
        
        # НОВОЕ: Проверяем статус администратора для клавиатуры
        is_admin = await is_user_admin(callback, state)
        
        # Get language info
        state_data = await state.get_data()
        current_language = state_data.get("current_language", {})
        
        # Extract word information
        word_number = current_word.get("word_number", "?")
        translation = current_word.get("translation", "Нет перевода")
        word_foreign = current_word.get("word_foreign", "")
        transcription = current_word.get("transcription", "")
        
        # Get updated user word data
        user_word_data = current_word.get("user_word_data", {})
        is_skipped = user_word_data.get("is_skipped", False)
        score = user_word_data.get("score", 0)
        check_interval = user_word_data.get("check_interval", 0)
        next_check_date = user_word_data.get("next_check_date")
        
        # Result message
        result_emoji = "✅" if known else "📝"
        result_text = "Отлично! Вы знаете это слово!" if known else "Слово для изучения"
        
        # Format message using centralized utility
        message_text = f"{result_emoji} <b>{result_text}</b>\n\n"
        
        message_text += format_study_word_message(
            language_name_ru=current_language.get("name_ru", "Неизвестный"),
            language_name_foreign=current_language.get("name_foreign", ""),
            word_number=word_number,
            translation=translation,
            is_skipped=is_skipped,
            score=score,
            check_interval=check_interval,
            next_check_date=next_check_date,
            score_changed=True,
            show_word=True,  # Always show word after evaluation
            word_foreign=word_foreign,
            transcription=transcription
        )
        
        # Add active hints if any using centralized utility
        used_hints = user_word_state.get_used_hints()
        if used_hints:
            hint_text = await format_used_hints(
                bot=callback.bot,
                user_id=user_word_state.user_id,
                word_id=user_word_state.word_id,
                current_word=current_word,
                used_hints=used_hints,
                include_header=True
            )
            message_text += hint_text
        
        # Add debug info if enabled
        if show_debug:
            # Use centralized debug function from study_words
            from app.bot.handlers.study.study_words import _get_debug_info
            debug_info = await _get_debug_info(state, user_word_state, hint_settings, is_admin)
            message_text = debug_info + '\n\n' + message_text
        
        # Create keyboard using centralized utility (ОБНОВЛЕНО: передаем is_admin)
        keyboard = create_adaptive_study_keyboard(
            word=current_word,
            word_shown=True,
            hint_settings=hint_settings,
            used_hints=used_hints,
            current_state=await state.get_state(),
            is_admin=is_admin,  # НОВОЕ: Передаем статус админа
        )
        
        # Send message
        await callback.message.edit_text(
            message_text,
            reply_markup=keyboard,
            parse_mode="HTML"
        )
        
    except Exception as e:
        logger.error(f"Error showing word result: {e}")
        await callback.message.answer("❌ Ошибка отображения результата")

async def _handle_batch_completion(
    callback: CallbackQuery, 
    state: FSMContext, 
    user_word_state: UserWordState
):
    """
    Handle completion of current word batch using centralized loading.
    FIXED: Uses centralized batch loading logic.
    
    Args:
        callback: The callback query
        state: FSM context
        user_word_state: Current word state
    """
    logger.info(f"Batch completion for user {user_word_state.user_id}")
    
    # Try to load next batch using centralized function
    api_client = get_api_client_from_bot(callback.bot)
    
    try:
        state_data = await state.get_data()
        current_language = state_data.get("current_language", {})
        language_id = current_language.get("id")
        
        if not language_id:
            logger.error("No language_id available for loading next batch")
            return False
        
        settings = user_word_state.study_settings

        batch_info = user_word_state.get_batch_info()
        db_user_id = user_word_state.user_id

        shift = user_word_state.get_next_batch_skip()
        batch_info["current_batch_index"] += 1

        (study_words, batch_info) = await load_next_batch(callback.message, batch_info, api_client, db_user_id, language_id, settings, shift)
        
        if (len(study_words) > 0):

            user_word_state.set_batch_info(batch_info)
            
            success = user_word_state.load_new_batch(study_words)
            if not success:
                logger.error(f"Error handling batch completion")
                await callback.answer("❌ Ошибка загрузки следующих слов")
                return False

            await user_word_state.save_to_state(state)
            logger.info(f"Successfully loaded next batch: {len(study_words)} words")

            # Batch loaded successfully
            await state.set_state(StudyStates.studying)
            await show_study_word(callback, state, user_word_state, need_new_message=True)
            
            # Get batch info for user feedback
            batch_info = user_word_state.get_batch_info()
            await callback.answer(f"📚 Загружена партия #{batch_info['current_batch_index']}")
            return
        
        # No more words available - use centralized completion handler
        from app.bot.handlers.study.study_words import handle_no_more_words
        await handle_no_more_words(callback, state, user_word_state)
        await callback.answer("🎉 Изучение завершено!")
        
    except Exception as e:
        logger.error(f"Error handling batch completion: {e}")
        await callback.answer("❌ Ошибка загрузки следующих слов")

# Export router
__all__ = ['word_actions_router']
