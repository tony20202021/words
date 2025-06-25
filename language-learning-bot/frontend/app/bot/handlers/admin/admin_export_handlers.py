"""
Handlers for words export functionality in administrative mode.
"""

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, BufferedInputFile
from aiogram.fsm.context import FSMContext
from datetime import datetime

from app.utils.api_utils import get_api_client_from_bot
from app.utils.logger import setup_logger
from app.bot.states.centralized_states import AdminStates
from app.bot.keyboards.admin_keyboards import (
    get_export_format_keyboard,
    get_export_range_keyboard,
    get_edit_language_keyboard
)
from app.utils.admin_utils import is_user_admin

# Создаем роутер для обработчиков экспорта
export_router = Router()

logger = setup_logger(__name__)


@export_router.callback_query(F.data.startswith("export_words_"))
async def process_export_words(callback: CallbackQuery, state: FSMContext):
    """
    Start words export process - show format selection.
    
    Args:
        callback: The callback query from Telegram
        state: The FSM state context
    """
    user_id = callback.from_user.id
    username = callback.from_user.username
    full_name = callback.from_user.full_name

    logger.info(f"'export_words_' callback from {full_name} ({username})")
    
    # Extract language ID from callback_data
    language_id = callback.data.split("_")[-1]
    
    # Check admin rights
    if not await is_user_admin(callback, state):
        await callback.message.answer("У вас нет прав администратора.")
        await callback.answer()
        return
    
    # Get API client
    api_client = get_api_client_from_bot(callback.bot)
    
    # Get language info
    language_response = await api_client.get_language(language_id)
    
    if not language_response["success"] or not language_response["result"]:
        error_msg = language_response.get("error", "Язык не найден")
        await callback.message.answer(f"Ошибка: {error_msg}")
        await callback.answer()
        logger.error(f"Failed to get language by ID {language_id}. Error: {error_msg}")
        return
    
    language = language_response["result"]
    
    # Get word count
    word_count_response = await api_client.get_word_count_by_language(language_id)
    word_count = 0
    if word_count_response["success"] and word_count_response["result"]:
        word_count = word_count_response["result"]["count"]
    
    # Set state and save data
    await state.set_state(AdminStates.selecting_export_format)
    await state.update_data(export_language_id=language_id)
    
    # Show format selection
    keyboard = get_export_format_keyboard(language_id)
    
    await callback.message.answer(
        f"📥 <b>Экспорт слов</b>\n\n"
        f"Язык: <b>{language['name_ru']}</b> ({language['name_foreign']})\n"
        f"Количество слов: <b>{word_count}</b>\n\n"
        f"Выберите формат для экспорта:",
        parse_mode="HTML",
        reply_markup=keyboard
    )
    
    await callback.answer()


@export_router.callback_query(AdminStates.selecting_export_format, F.data.startswith("export_format_"))
async def process_export_format(callback: CallbackQuery, state: FSMContext):
    """
    Process export format selection - show range options.
    
    Args:
        callback: The callback query from Telegram
        state: The FSM state context
    """
    user_id = callback.from_user.id
    username = callback.from_user.username
    full_name = callback.from_user.full_name

    logger.info(f"'export_format_' callback from {full_name} ({username})")
    
    # Parse callback data: export_format_{language_id}_{format}
    parts = callback.data.split("_")
    language_id = parts[2]
    format = parts[3]
    
    # Update state data
    await state.update_data(export_format=format)
    await state.set_state(AdminStates.selecting_export_range)
    
    # Format names for display
    format_names = {
        "xlsx": "Excel (.xlsx)",
        "csv": "CSV (.csv)", 
        "json": "JSON (.json)"
    }
    format_display = format_names.get(format, format.upper())
    
    # Show range selection
    keyboard = get_export_range_keyboard(language_id, format)
    
    await callback.message.answer(
        f"📊 <b>Выбран формат:</b> {format_display}\n\n"
        f"Выберите диапазон слов для экспорта:",
        parse_mode="HTML",
        reply_markup=keyboard
    )
    
    await callback.answer()


@export_router.callback_query(AdminStates.selecting_export_range, F.data.startswith("export_range_"))
async def process_export_range(callback: CallbackQuery, state: FSMContext):
    """
    Process export range selection.
    
    Args:
        callback: The callback query from Telegram
        state: The FSM state context
    """
    user_id = callback.from_user.id
    username = callback.from_user.username
    full_name = callback.from_user.full_name

    logger.info(f"'export_range_' callback from {full_name} ({username})")
    
    # Parse callback data: export_range_{language_id}_{format}_{range_type}
    parts = callback.data.split("_")
    language_id = parts[2]
    format = parts[3]
    range_type = parts[4]
    
    if range_type == "all":
        # Export all words immediately
        await export_words_file(callback, state, language_id, format, None, None)
    elif range_type == "range":
        # Ask for range input
        await state.set_state(AdminStates.entering_export_range)
        await state.update_data(
            export_language_id=language_id,
            export_format=format
        )
        
        await callback.message.answer(
            "🔢 <b>Укажите диапазон слов</b>\n\n"
            "Введите диапазон в формате: <code>начало-конец</code>\n"
            "Например: <code>1-100</code> или <code>50-200</code>\n\n"
            "Или введите только начальное число для экспорта с этого номера до конца.",
            parse_mode="HTML"
        )
    
    await callback.answer()


@export_router.message(AdminStates.entering_export_range)
async def process_export_range_input(message: Message, state: FSMContext):
    """
    Process export range input from admin.
    
    Args:
        message: The message object from Telegram
        state: The FSM state context
    """
    user_data = await state.get_data()
    language_id = user_data.get('export_language_id')
    format = user_data.get('export_format')
    
    if not language_id or not format:
        await message.answer("❌ Ошибка: данные экспорта не найдены. Начните экспорт заново.")
        await state.clear()
        return
    
    # Parse range input
    range_text = message.text.strip()
    start_word = None
    end_word = None
    
    try:
        if "-" in range_text:
            # Range format: start-end
            parts = range_text.split("-", 1)
            start_word = int(parts[0].strip())
            end_word = int(parts[1].strip()) if parts[1].strip() else None
        else:
            # Single number: start from this number
            start_word = int(range_text)
            end_word = None
        
        if start_word <= 0:
            await message.answer("❌ Начальный номер должен быть больше 0.")
            return
        
        if end_word is not None and end_word < start_word:
            await message.answer("❌ Конечный номер должен быть больше начального.")
            return
        
    except ValueError:
        await message.answer(
            "❌ Неверный формат диапазона.\n"
            "Используйте формат: <code>1-100</code> или <code>50</code>",
            parse_mode="HTML"
        )
        return
    
    # Export with specified range
    await export_words_file(message, state, language_id, format, start_word, end_word, is_callback=False)


async def export_words_file(
    message_or_callback, 
    state: FSMContext, 
    language_id: str, 
    format: str, 
    start_word: int = None, 
    end_word: int = None,
    is_callback: bool = True
):
    """
    Export words file and send to admin.
    
    Args:
        message_or_callback: The message or callback object from Telegram
        state: The FSM state context
        language_id: ID of the language to export
        format: Export format (xlsx, csv, json)
        start_word: Optional start word number
        end_word: Optional end word number
        is_callback: Whether this is called from a callback handler
    """
    if is_callback:
        message = message_or_callback.message
        user_id = message_or_callback.from_user.id
    else:
        message = message_or_callback
        user_id = message.from_user.id
    
    # Show processing message
    range_text = ""
    if start_word is not None:
        if end_word is not None:
            range_text = f" (слова {start_word}-{end_word})"
        else:
            range_text = f" (с {start_word} слова)"
    
    processing_msg = await message.answer(
        f"⏳ Экспортирую слова в формате {format.upper()}{range_text}...\n"
        f"Это может занять некоторое время."
    )
    
    # Get API client
    api_client = get_api_client_from_bot(message.bot)
    
    try:
        # Call export API
        export_response = await api_client.export_words_by_language(
            language_id=language_id,
            format=format,
            start_word=start_word,
            end_word=end_word,
            timeout_multiplier=10  # Increased timeout for large exports
        )
        
        if not export_response["success"]:
            error_msg = export_response.get("error", "Неизвестная ошибка")
            await processing_msg.edit_text(f"❌ Ошибка экспорта: {error_msg}")
            logger.error(f"Failed to export words for language {language_id}. Error: {error_msg}")
            await state.clear()
            return
        
        file_data = export_response["result"]
        
        if not file_data:
            await processing_msg.edit_text("❌ Получен пустой файл экспорта.")
            await state.clear()
            return
        
        # Get language info for filename
        language_response = await api_client.get_language(language_id)
        language_name = "unknown"
        if language_response["success"] and language_response["result"]:
            language_name = language_response["result"]["name_ru"]
        
        # Generate filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        language_name_safe = "".join(c for c in language_name if c.isalnum() or c in (' ', '-', '_')).rstrip()
        
        range_suffix = ""
        if start_word is not None:
            if end_word is not None:
                range_suffix = f"_{start_word}-{end_word}"
            else:
                range_suffix = f"_{start_word}-end"
        
        filename = f"words_{language_name_safe}{range_suffix}_{timestamp}.{format}"
        
        # Determine MIME type
        mime_types = {
            "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "csv": "text/csv",
            "json": "application/json"
        }
        
        # Create BufferedInputFile for sending
        input_file = BufferedInputFile(
            file_data,
            filename=filename
        )
        
        # Delete processing message
        await processing_msg.delete()
        
        # Send file
        caption = (
            f"📥 <b>Экспорт слов завершен</b>\n\n"
            f"Язык: <b>{language_name}</b>\n"
            f"Формат: <b>{format.upper()}</b>\n"
            f"Размер: <b>{len(file_data)} байт</b>"
        )
        
        if range_text:
            caption += f"\nДиапазон: <b>{range_text.strip('() ')}</b>"
        
        await message.answer_document(
            document=input_file,
            caption=caption,
            parse_mode="HTML"
        )
        
        # Return to language edit screen
        await state.set_state(AdminStates.viewing_language_details)
        
        # Show language edit keyboard
        keyboard = get_edit_language_keyboard(language_id)
        await message.answer(
            "✅ Экспорт завершен! Возвращаемся к редактированию языка.",
            reply_markup=keyboard
        )
        
        logger.info(f"Successfully exported {len(file_data)} bytes for language {language_id} "
                   f"in format {format} for user {user_id}")
        
    except Exception as e:
        logger.error(f"Error during export: {e}", exc_info=True)
        await processing_msg.edit_text(
            f"❌ Ошибка при экспорте: {str(e)}"
        )
        await state.clear()
        