"""
Handlers for language selection during file upload.
Updated with FSM states for better navigation control.
"""

from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext
from app.utils.api_utils import get_api_client_from_bot
from app.utils.logger import setup_logger
from app.bot.states.centralized_states import AdminStates

logger = setup_logger(__name__)

# Создаем роутер для обработчиков выбора языка
language_router = Router()

@language_router.callback_query(F.data.startswith("upload_to_lang_"))
async def process_language_selection_for_upload(callback: CallbackQuery, state: FSMContext):
    """
    Process language selection for file upload.
    
    Args:
        callback: The callback query from Telegram
        state: The FSM state context
    """
    # Добавляем логирование
    user = callback.from_user
    logger.info(f"'upload_to_lang_' callback from {user.full_name} ({user.username})")
    
    # Извлекаем ID языка из callback_data
    language_id = callback.data.split("_")[-1]
    
    # Логируем ID языка
    logger.info(f"Selected language ID for upload: {language_id}")
    
    # Получаем клиент API с помощью утилиты
    api_client = get_api_client_from_bot(callback.bot)
    
    # Получаем информацию о языке
    language_response = await api_client.get_language(language_id)
    
    if not language_response["success"] or not language_response["result"]:
        error_msg = language_response.get("error", "Язык не найден")
        await callback.message.answer(f"Ошибка: {error_msg}")
        await callback.answer()
        logger.error(f"Failed to get language by ID {language_id}. Error: {error_msg}")
        return
    
    language = language_response["result"]
    
    # Сохраняем данные в состоянии
    await state.update_data(selected_language_id=language_id)
    
    # ✅ НОВОЕ: Устанавливаем состояние ожидания файла
    await state.set_state(AdminStates.waiting_file)
    
    await callback.message.answer(
        f"📤 Отправьте Excel-файл со списком слов для языка: {language['name_ru']}.\n\n"
        "Требования к файлу:\n"
        "- Формат: .xlsx\n"
        "- Должны быть колонки с номером, словом на иностранном языке, "
        "транскрипцией и переводом\n"
        "- Порядок колонок можно будет настроить после загрузки"
    )
    
    # Отвечаем на callback
    await callback.answer()

# ✅ НОВОЕ: Обработчик для отмены выбора языка (возврат к выбору языка)
@language_router.callback_query(AdminStates.waiting_file, F.data == "cancel_language_selection")
async def process_cancel_language_selection(callback: CallbackQuery, state: FSMContext):
    """
    Handle canceling language selection and returning to language list.
    
    Args:
        callback: The callback query from Telegram
        state: The FSM state context
    """
    logger.info("Cancel language selection for upload")
    
    # Очищаем выбранный язык из состояния
    user_data = await state.get_data()
    if 'selected_language_id' in user_data:
        del user_data['selected_language_id']
        await state.set_data(user_data)
    
    # Возвращаемся к выбору языка (эмулируем команду /upload)
    from app.bot.handlers.admin.file_upload.file_processing import cmd_upload
    
    # Создаем фиктивное сообщение для переиспользования логики
    fake_message = callback.message
    fake_message.from_user = callback.from_user
    
    await cmd_upload(fake_message, state)
    await callback.answer()

# ✅ НОВОЕ: Обработчик для команд в состоянии ожидания файла
@language_router.callback_query(AdminStates.waiting_file, F.data.startswith("upload_to_lang_"))
async def process_change_language_during_upload(callback: CallbackQuery, state: FSMContext):
    """
    Handle changing language selection during file upload process.
    
    Args:
        callback: The callback query from Telegram
        state: The FSM state context
    """
    logger.info("Changing language selection during upload process")
    
    # Обрабатываем как обычный выбор языка
    await process_language_selection_for_upload(callback, state)
    