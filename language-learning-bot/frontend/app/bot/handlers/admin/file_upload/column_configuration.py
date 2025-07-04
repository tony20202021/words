"""
Handlers for column configuration during file upload.
Updated with FSM states for better navigation control.
"""

from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext
from app.utils.api_utils import get_api_client_from_bot
from app.utils.logger import setup_logger
from app.bot.states.centralized_states import AdminStates
from app.utils.callback_constants import CallbackData

logger = setup_logger(__name__)

# Создаем роутер для обработчиков настройки колонок
column_router = Router()

# Константы для настроек колонок по умолчанию
DEFAULT_COLUMN_NUMBER = 0
DEFAULT_COLUMN_WORD = 1
DEFAULT_COLUMN_TRANSCRIPTION = 2
DEFAULT_COLUMN_TRANSLATION = 3

@column_router.callback_query(AdminStates.configuring_columns, F.data == CallbackData.CONFIRM_UPLOAD)
async def process_upload_confirmation(callback: CallbackQuery, state: FSMContext):
    """
    Process upload confirmation after column configuration.
    
    Args:
        callback: The callback query from Telegram
        state: The FSM state context
    """
    logger.info("Processing upload confirmation from column configuration")
    
    # Устанавливаем состояние подтверждения загрузки файла
    await state.set_state(AdminStates.confirming_file_upload)
    
    # Получаем данные состояния
    user_data = await state.get_data()
    logger.debug(f"User data for upload confirmation: {user_data}")
    
    # Проверяем, что все необходимые колонки настроены
    # Если они не настроены, используем значения по умолчанию
    if user_data.get('column_word') is None:
        await state.update_data(column_word=DEFAULT_COLUMN_WORD)
        
    if user_data.get('column_translation') is None:
        await state.update_data(column_translation=DEFAULT_COLUMN_TRANSLATION)
        
    if user_data.get('column_number') is None:
        await state.update_data(column_number=DEFAULT_COLUMN_NUMBER)
        
    if user_data.get('column_transcription') is None:
        await state.update_data(column_transcription=DEFAULT_COLUMN_TRANSCRIPTION)
    
    # Получаем обновленные данные состояния
    user_data = await state.get_data()
    
    # Получаем клиент API с помощью утилиты
    api_client = get_api_client_from_bot(callback.bot)
    
    # Подготавливаем данные для загрузки
    language_id = user_data.get('selected_language_id')
    file_data = user_data.get('file_data')
    file_name = user_data.get('file_name')
    
    # Формируем параметры для API, сохраняя стиль именования
    api_params = {
        "column_word": user_data.get('column_word'),
        "column_translation": user_data.get('column_translation'),
        "column_transcription": user_data.get('column_transcription'),
        "column_number": user_data.get('column_number'),
        "start_row": 1 if user_data.get('has_headers', False) else 0,  # Если есть заголовки, начинаем с 1, иначе с 0
        "clear_existing": user_data.get('clear_existing', False)  # Параметр для очистки существующих слов
    }
    
    # Загружаем файл через API
    try:
        loading_message = await callback.message.answer("⏳ Загрузка файла...")
        
        upload_response = await api_client.upload_words_file(
            language_id=language_id,
            file_data=file_data,
            file_name=file_name,
            params=api_params,
            timeout_multiplier=5  # Увеличенный таймаут для большого файла
        )
        
        logger.debug(f"Upload file response: {upload_response}")
        
        if not upload_response["success"]:
            error_msg = upload_response.get("error", "Неизвестная ошибка")
            await loading_message.edit_text(f"❌ Ошибка при загрузке файла: {error_msg}")
            logger.error(f"Failed to upload file. Error: {error_msg}")
            # Возвращаемся к настройкам загрузки при ошибке
            await state.set_state(AdminStates.configuring_upload_settings)
            return
        
        result = upload_response["result"]
        
        # Обновляем сообщение с результатом
        await loading_message.edit_text(
            f"✅ Файл успешно загружен!\n\n"
            f"Язык: {result.get('language_name')}\n"
            f"Обработано слов: {result.get('total_words_processed')}\n"
            f"Добавлено: {result.get('words_added')}\n"
            f"Обновлено: {result.get('words_updated')}\n"
            f"Пропущено: {result.get('words_skipped')}\n" # TODO показать первые 3 слова и многоточие
            f"Ошибки: {len(result.get('errors', []))}" # TODO показать первые 3 слова и многоточие
        )
        
        # Если есть ошибки, логируем их
        if result.get('errors') and len(result.get('errors', [])) > 0:
            logger.warning(f"Errors during file upload: {result.get('errors')}")
        
        # Очищаем состояние и возвращаемся в главное меню админа
        await state.clear()
        
        # Показываем кнопку возврата в админ-панель
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Вернуться в админку", callback_data=CallbackData.BACK_TO_ADMIN)]
        ])
        
        await callback.message.answer(
            "🎉 Загрузка файла завершена!\n\n"
            "Вы можете вернуться в административную панель или выполнить другие действия.",
            reply_markup=keyboard
        )
        
    except Exception as e:
        logger.error(f"Error uploading file: {e}")
        await loading_message.edit_text(
            f"❌ Ошибка при загрузке файла: {str(e)}"
        )
        # Возвращаемся к настройкам загрузки при исключении
        await state.set_state(AdminStates.configuring_upload_settings)
    
    await callback.answer()

# Обработчик отмены из конфигурации колонок
@column_router.callback_query(AdminStates.configuring_columns, F.data == CallbackData.BACK_TO_SETTINGS)
async def process_back_to_settings_from_columns(callback: CallbackQuery, state: FSMContext):
    """
    Handle going back to upload settings from column configuration.
    
    Args:
        callback: The callback query from Telegram
        state: The FSM state context
    """
    logger.info("Back to settings from column configuration")
    
    # ✅ НОВОЕ: Возвращаемся к состоянию настроек загрузки
    await state.set_state(AdminStates.configuring_upload_settings)
    
    # Импортируем и вызываем обработчик возврата к настройкам
    from app.bot.handlers.admin.file_upload.settings_management import process_back_to_settings
    await process_back_to_settings(callback, state)

# ✅ НОВОЕ: Обработчик возврата в админку из конфигурации колонок
@column_router.callback_query(AdminStates.configuring_columns, F.data == CallbackData.BACK_TO_ADMIN)
async def process_back_to_admin_from_columns(callback: CallbackQuery, state: FSMContext):
    """
    Handle going back to admin menu from column configuration.
    
    Args:
        callback: The callback query from Telegram
        state: The FSM state context
    """
    logger.info("Back to admin from column configuration")
    
    # Очищаем состояние загрузки файла
    await state.clear()
    
    # Импортируем и вызываем функцию возврата в административное меню
    from app.bot.handlers.admin.admin_basic_handlers import handle_admin_mode
    await handle_admin_mode(callback, state, is_callback=True)
    
    await callback.answer()

# ✅ НОВОЕ: Обработчик для состояния подтверждения загрузки файла
@column_router.callback_query(AdminStates.confirming_file_upload, F.data == CallbackData.BACK_TO_ADMIN)
async def process_back_to_admin_from_confirmation(callback: CallbackQuery, state: FSMContext):
    """
    Handle going back to admin menu from upload confirmation.
    
    Args:
        callback: The callback query from Telegram
        state: The FSM state context
    """
    logger.info("Back to admin from upload confirmation")
    
    # Очищаем состояние
    await state.clear()
    
    # Импортируем и вызываем функцию возврата в административное меню
    from app.bot.handlers.admin.admin_basic_handlers import handle_admin_mode
    await handle_admin_mode(callback, state, is_callback=True)
    
    await callback.answer()
    