"""
Handlers for word display actions during the study process.
Обработчики для отображения слов в процессе изучения.
UPDATED: Added writing image support.
UPDATED: Removed hieroglyphic language restrictions - controlled by user settings only.
"""

from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.types import BufferedInputFile

from app.utils.logger import setup_logger
from app.utils.state_models import UserWordState
from app.utils.word_data_utils import update_word_score
from app.utils.callback_constants import CallbackData
from app.bot.states.centralized_states import StudyStates
from app.bot.handlers.study.study_words import show_study_word
from app.utils.word_image_generator import generate_word_image
from app.bot.keyboards.study_keyboards import create_word_image_keyboard, create_writing_image_keyboard
from app.utils.writing_image_generator import generate_writing_image
from app.utils.settings_utils import is_writing_images_enabled

logger = setup_logger(__name__)

# Создаем роутер для обработчиков отображения слов
display_router = Router()

@display_router.callback_query(F.data == CallbackData.SHOW_WORD, StudyStates.studying)
@display_router.callback_query(F.data == CallbackData.SHOW_WORD, StudyStates.confirming_word_knowledge)
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


@display_router.callback_query(F.data == CallbackData.SHOW_WORD_IMAGE)
async def process_show_word_image_callback(callback: CallbackQuery, state: FSMContext):
    logger.info(f"'show_word_image' callback from {callback.from_user.full_name}")
    
    # Show word image using common function
    await _show_word_image(callback, state)


@display_router.message(Command("show_big"))
async def cmd_show_big_word(message: Message, state: FSMContext):
    logger.info(f"'/show_big' command from {message.from_user.full_name}")
    
    # Show word image using common function
    await _show_word_image(message, state)


@display_router.callback_query(F.data == CallbackData.BACK_FROM_IMAGE, StudyStates.viewing_word_image)
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


# Writing image handlers

@display_router.callback_query(F.data == CallbackData.SHOW_WRITING_IMAGE)
async def process_show_writing_image_callback(callback: CallbackQuery, state: FSMContext):
    """
    Process 'Show writing image' action.
    UPDATED: Removed hieroglyphic language restrictions - controlled by user settings only.
    
    Args:
        callback: The callback query
        state: FSM context
    """
    logger.info(f"'show_writing_image' callback from {callback.from_user.full_name}")
    
    # Show writing image using common function
    await _show_writing_image(callback, state)


@display_router.message(Command("show_writing"))
async def cmd_show_writing_image(message: Message, state: FSMContext):
    """
    Command to show writing image for current word.
    
    Args:
        message: The message object
        state: FSM context
    """
    logger.info(f"'/show_writing' command from {message.from_user.full_name}")
    
    # Show writing image using common function
    await _show_writing_image(message, state)


@display_router.callback_query(F.data == CallbackData.BACK_FROM_WRITING_IMAGE, StudyStates.viewing_writing_image)
async def process_back_from_writing_image(callback: CallbackQuery, state: FSMContext):
    """
    Обработчик возврата от картинки написания к экрану изучения.
    
    Args:
        callback: The callback query
        state: FSM context
    """
    logger.info(f"'back_from_writing_image' callback from {callback.from_user.full_name}")
    
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
    
    # Show study word again
    await show_study_word(callback, state, user_word_state, need_new_message=True)
    await callback.answer("⬅️ Возвращаемся к изучению")


async def _show_word_image(
    message_or_callback, 
    state: FSMContext, 
):
    """
    Общая функция для показа изображения слова.
    
    Args:
        message_or_callback: Message or CallbackQuery object
        state: FSM context
    """
    if hasattr(message_or_callback, 'answer'):
        message = message_or_callback
    else:
        message = message_or_callback.message

    try:
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

        # Extract word and transcription
        word_foreign = current_word.get("word_foreign", "")
        transcription = current_word.get("transcription", "")
        
        if not word_foreign:
            error_msg = "❌ Слово на иностранном языке не найдено"
            await message.answer(error_msg)
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
        await message.answer("🔍 Показываю крупное написание")
        await message.answer_photo(
            photo=input_file,
            caption=caption,
            reply_markup=keyboard,
            parse_mode="HTML"
        )
        
        logger.info(f"Successfully sent word image for: {word_foreign}")
        
    except Exception as e:
        logger.error(f"Error showing word image: {e}", exc_info=True)
        
        error_msg = "❌ Ошибка при создании изображения слова"
        await message.answer(error_msg)


async def _show_writing_image(
    message_or_callback, 
    state: FSMContext,
):
    """
    Общая функция для показа картинки написания.
    UPDATED: Removed hieroglyphic language restrictions - controlled by user settings only.
    
    Args:
        message_or_callback: Message or CallbackQuery object
        state: FSM context
    """
    if hasattr(message_or_callback, 'answer'):
        message = message_or_callback
    else:
        message = message_or_callback.message

    try:
        # Check if writing images are enabled for user
        if not await is_writing_images_enabled(message_or_callback, state):
            await message.answer("❌ Картинки написания отключены в настройках")
            return

        # Get current word state
        user_word_state = await UserWordState.from_state(state)
        
        if not user_word_state.is_valid() or not user_word_state.has_more_words():
            await message.answer("❌ Нет активного слова для показа картинки написания")
            return
        
        # Get current word
        current_word = user_word_state.get_current_word()
        if not current_word:
            await message.answer("❌ Ошибка получения текущего слова")
            return

        # Extract word
        word_foreign = current_word.get("word_foreign", "")
        
        if not word_foreign:
            await message.answer("❌ Слово на иностранном языке не найдено")
            return

        # Get language info
        state_data = await state.get_data()
        current_language = state_data.get("current_language", {})
        language_code = current_language.get("name_foreign", "").lower()
        
        # Generate writing image using stub
        logger.info(f"Generating writing image for word: '{word_foreign}', language: '{language_code}'")
        
        await message.answer("🖼️ Генерирую картинку написания...")
        
        image_buffer = await generate_writing_image(
            word=word_foreign,
            language=language_code
        )
        
        # Create BufferedInputFile from BytesIO for Telegram
        image_buffer.seek(0)  # Reset buffer position
        input_file = BufferedInputFile(
            file=image_buffer.read(),
            filename=f"writing_{word_foreign}.png"
        )
        
        # Prepare caption
        caption = f"🖼️ Картинка написания для: <b>{word_foreign}</b>"
        
        # Create keyboard
        keyboard = create_writing_image_keyboard()
        
        # Set state
        await state.set_state(StudyStates.viewing_writing_image)
        
        # Send image
        await message.answer_photo(
            photo=input_file,
            caption=caption,
            reply_markup=keyboard,
            parse_mode="HTML"
        )
        
        logger.info(f"Successfully sent writing image for: {word_foreign}")
        
    except Exception as e:
        logger.error(f"Error showing writing image: {e}", exc_info=True)
        
        error_msg = "❌ Ошибка при создании картинки написания"
        await message.answer(error_msg)
        