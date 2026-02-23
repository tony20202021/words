"""
Handlers for word display actions during the study process.
Обработчики для отображения слов в процессе изучения.
"""

import io
from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.types import BufferedInputFile, InputMediaPhoto

from app.utils.logger import setup_logger
from app.utils.state_models import UserWordState
from app.utils.word_data_utils import update_word_score
from app.utils.callback_constants import CallbackData
from app.bot.states.centralized_states import StudyStates
from app.bot.handlers.study.study_words import show_study_word
from app.utils.big_word_generator import generate_big_word
from app.bot.keyboards.study_keyboards import create_word_image_keyboard, create_writing_image_keyboard
from app.api.writing_image_client import get_writing_image_client
from app.utils.settings_utils import is_writing_images_enabled, get_user_language_settings
from app.utils.message_utils import get_message_from_callback
from app.utils.error_utils import validate_state_data
from app.utils.word_data_utils import get_hint_text
from app.utils.formatting_utils import generate_big_word_message


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
        logger.error(f"Invalid user_word_state: {user_word_state}")
        return
    
    # Get current word
    current_word = user_word_state.get_current_word()
    if not current_word:
        await callback.answer("❌ Ошибка получения текущего слова")
        logger.error(f"No current word: {current_word}")
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
        logger.error(f"Error updating word score: {result}")
        return

    # Update local word data
    if "user_word_data" not in current_word:
        current_word["user_word_data"] = {}

    current_word["user_word_data"].update(result or {})
    current_word["user_word_data"]["score"] = 0
    
    # Mark word as processed and set flags
    user_word_state.set_current_word(current_word)
    user_word_state.set_flag("word_shown", True)
    user_word_state.mark_word_as_processed()
    
    # Save state and transition
    await user_word_state.save_to_state(state)
    await state.set_state(StudyStates.viewing_word_details)
    
    # Use centralized display function
    await show_study_word(callback, state, user_word_state, need_new_message=False)
    
    await callback.answer("👁️ Показываю слово")


@display_router.callback_query(F.data == CallbackData.SHOW_BIG)
async def callback_show_big(callback: CallbackQuery, state: FSMContext):
    logger.info(f"'callback_show_big' callback from {callback.from_user.full_name}")
    
    # Show word image using common function
    await process_show_big(callback, state)


@display_router.message(Command("show_big"))
async def cmd_show_big(message: Message, state: FSMContext):
    logger.info(f"'/show_big' command from {message.from_user.full_name}")
    
    # Show word image using common function
    await process_show_big(message, state)


@display_router.callback_query(F.data == CallbackData.BACK_FROM_BIG, StudyStates.viewing_word_image)
async def process_back_from_big(callback: CallbackQuery, state: FSMContext):
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
async def callback_show_writing_image(callback: CallbackQuery, state: FSMContext):
    """
    Process 'Show writing image' action.
    UPDATED: Removed hieroglyphic language restrictions - controlled by user settings only.
    
    Args:
        callback: The callback query
        state: FSM context
    """
    logger.info(f"'callback_show_writing_image' callback from {callback.from_user.full_name}")
    
    # Show writing image using common function
    await process_show_writing_image(callback, state)


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
    await process_show_writing_image(message, state)


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


async def process_show_big(
    message_or_callback, 
    state: FSMContext, 
):
    """
    Общая функция для показа изображения слова.
    
    Args:
        message_or_callback: Message or CallbackQuery object
        state: FSM context
    """
    message = get_message_from_callback(message_or_callback)

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
        
        input_file = await generate_big_word_message(
            word_foreign,
            transcription,
        )

        caption = ""
        keyboard = create_word_image_keyboard()
        
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


async def process_show_writing_image(
    message_or_callback, 
    state: FSMContext,
):
    """
    Общая функция для показа картинки написания.
    UPDATED: Removed hieroglyphic language restrictions - controlled by user settings only.
    UPDATED: Replaced local generator with real service client.
    
    Args:
        message_or_callback: Message or CallbackQuery object
        state: FSM context
    """
    message = get_message_from_callback(message_or_callback)

    try:
        # Check if writing images are enabled for user
        if not await is_writing_images_enabled(message_or_callback, state):
            await message.answer("❌ Картинки написания отключены в настройках")
            return

        # Validate state data
        is_valid, state_data = await validate_state_data(
            state, 
            ["db_user_id"],
            message_or_callback,
            "Ошибка: недостаточно данных"
        )

        # Load user settings including individual hint settings
        settings = await get_user_language_settings(message_or_callback, state)
        show_debug = settings.get('show_debug', False)

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
        translation = current_word.get("translation", "")

        db_user_id = user_word_state.user_id
        word_id = user_word_state.word_id
        hint_key = "hint_writing"
        
        hint_writing = await get_hint_text(
            message_or_callback.bot, 
            db_user_id, 
            word_id, 
            hint_key, 
            current_word
        )
       
        if not word_foreign:
            await message.answer("❌ Слово на иностранном языке не найдено")
            return

        # Generate writing image using real service
        logger.info(f"Generating writing image for word: '{word_foreign}', translation: '{translation}'")
        
        await message.answer("🖼️ Генерирую картинку написания...\n\n Ожидаемое время: около 10 секунд...")
        
        # Get writing image client and call service
        client = get_writing_image_client()
        request_result = await client.generate_writing_image(
            word=word_foreign,
            translation=translation,
            hint_writing=hint_writing,
            show_debug=show_debug,
        )
        logger.info(f"Writing image result: {request_result['success']}")
        
        if not request_result["success"]:
            error_msg = f"❌ Ошибка сервиса генерации: {request_result.get('error', 'Неизвестная ошибка')}"
            await message.answer(error_msg)
            return
        
        image_result = request_result["result"]
        
        # Get image data from result
        base_image = image_result["base_image"]
        if base_image is not None:
            image_buffer = io.BytesIO(base_image)
            image_buffer.seek(0)  # Reset buffer position
            input_file = BufferedInputFile(
                file=image_buffer.read(),
                filename=f"base_image_{word_foreign}.png"
            )

            caption = f"base_image: <b>{word_foreign}</b>"
            await message.answer_photo(
                photo=input_file,
                caption=caption,
            )
        else:
            logger.warning(f"Base image is None for word: {word_foreign}")
            await message.answer("Base image is None for word: {word_foreign}")

        conditioning_images = image_result["conditioning_images"]
        for key_type in conditioning_images.keys():
            media = []
            newline = '\n'
            caption = f"{key_type}:{newline} {f',{newline}'.join([key_method if image is not None else f'{key_method}: (None)' for key_method, image in conditioning_images[key_type].items()])}"
            first = True  # Caption можно указать только к первому элементу

            for key_method, image in conditioning_images[key_type].items():
                if image is not None:
                    file = BufferedInputFile(image, filename=f"conditioning_{key_type}_{key_method}.png")

                    input_media = InputMediaPhoto(
                        media=file,
                        caption=f"{caption}" if first else None,
                        parse_mode="HTML" if first else None
                    )
                    media.append(input_media)
                    first = False

            await message.answer_media_group(media=media)

        caption = f"prompt_used: {image_result['prompt_used']}"
        await message.answer(caption)

        caption = f"generation_metadata: {image_result['generation_metadata']}"
        await message.answer(caption)

        # Prepare caption
        caption = f"🖼️ Картинка написания для: <b>{word_foreign}</b>\n\n"
        if show_debug:
            caption += f"success: {image_result['success']}\n"
            caption += f"status: {image_result['status']}\n"
            caption += f"error: {image_result['error']}\n"
            caption += f"warnings: {image_result['warnings']}\n"
        
        # Create keyboard
        keyboard = create_writing_image_keyboard()
        
        # Set state
        await state.set_state(StudyStates.viewing_writing_image)
        
        # Get image data from result
        generated_image = image_result["generated_image"]
        image_buffer = io.BytesIO(generated_image)
        image_buffer.seek(0)  # Reset buffer position
        input_file = BufferedInputFile(
            file=image_buffer.read(),
            filename=f"writing_{word_foreign}.png"
        )

        # Send image
        await message.answer_photo(
            photo=input_file,
            caption=caption,
            reply_markup=keyboard,
            parse_mode="HTML",
        )

        logger.info(f"Successfully sent writing image for: {word_foreign}")
        
    except Exception as e:
        logger.error(f"Error showing writing image: {e}", exc_info=True)
        
        error_msg = "❌ Ошибка при создании картинки написания"
        await message.answer(error_msg)
        