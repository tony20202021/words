"""
Handlers for language selection during file upload.
"""

from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext
from app.utils.api_utils import get_api_client_from_bot
from app.utils.logger import setup_logger
from app.bot.handlers.admin.admin_states import AdminStates

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
    
    await callback.message.answer(
        f"📤 Отправьте Excel-файл со списком слов для языка: {language['name_ru']}.\n\n"
        "Требования к файлу:\n"
        "- Формат: .xlsx\n"
        "- Должны быть колонки с номером, словом на иностранном языке, "
        "транскрипцией и переводом\n"
        "- Порядок колонок можно будет настроить после загрузки"
    )
    
    # Переходим в состояние ожидания файла
    await state.set_state(AdminStates.waiting_file)
    await callback.answer()