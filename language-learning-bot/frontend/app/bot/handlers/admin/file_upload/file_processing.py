"""
Handlers for file upload processing.
Updated with FSM states for better navigation control.
"""

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardButton, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
from app.utils.api_utils import get_api_client_from_bot
from app.utils.logger import setup_logger
from app.bot.states.centralized_states import AdminStates
from app.utils.callback_constants import CallbackData
from app.bot.keyboards.admin_keyboards import get_upload_settings_keyboard

logger = setup_logger(__name__)

# Создаем роутер для обработчиков загрузки файла
file_router = Router()

# TODO добавить параметр - очистить статистику всех пользователей по этому языку
# реализовать как отдельную функцию clien API
# и добавить  вызов этой функции (очистить статистику всех пользователей по выбранному языку) - в админ/управление языком
# сделать нужные изменения в client API, backend

# Константы для настроек колонок по умолчанию
DEFAULT_COLUMN_NUMBER = 0
DEFAULT_COLUMN_WORD = 1
DEFAULT_COLUMN_TRANSCRIPTION = 2
DEFAULT_COLUMN_TRANSLATION = 3

@file_router.message(Command("upload"))
async def cmd_upload(message: Message, state: FSMContext):
    """
    Handle the /upload command which starts file upload process.
    
    Args:
        message: The message object from Telegram
        state: The FSM state context
    """
    user_id = message.from_user.id
    username = message.from_user.username
    full_name = message.from_user.full_name

    logger.info(f"'/upload' command from {full_name} ({username})")
    
    # Получаем клиент API с помощью утилиты
    api_client = get_api_client_from_bot(message.bot)
    
    # Проверяем права администратора
    user_response = await api_client.get_user_by_telegram_id(user_id)
    
    if not user_response["success"]:
        error_msg = user_response.get("error", "Неизвестная ошибка")
        await message.answer(f"Ошибка при получении данных пользователя: {error_msg}")
        logger.error(f"Failed to get user data during /upload command. Error: {error_msg}")
        return
    
    # Получаем пользователя из ответа
    users = user_response["result"]
    user = users[0] if users and isinstance(users, list) and len(users) > 0 else None
    
    if not user or not user.get("is_admin", False):
        await message.answer("У вас нет прав администратора.")
        return
    
    # Получаем список языков из API
    languages_response = await api_client.get_languages()
    
    if not languages_response["success"]:
        error_msg = languages_response.get("error", "Неизвестная ошибка")
        await message.answer(f"Ошибка при получении списка языков: {error_msg}")
        logger.error(f"Failed to get languages during /upload command. Error: {error_msg}")
        return
    
    languages = languages_response["result"] or []
    
    if not languages or len(languages) == 0:
        await message.answer(
            "📤 Сначала необходимо создать хотя бы один язык через команду /managelang"
        )
        return
    
    # Создаем клавиатуру с доступными языками
    # Используем InlineKeyboardBuilder
    builder = InlineKeyboardBuilder()
    
    for language in languages:
        builder.add(InlineKeyboardButton(
            text=f"{language['name_ru']} ({language['name_foreign']})",
            callback_data=f"upload_to_lang_{language['id']}"
        ))
    
    # Настраиваем ширину строки клавиатуры (по 1 кнопке в ряд)
    builder.adjust(1)
    
    await message.answer(
        "📤 Выберите язык для загрузки слов:",
        reply_markup=builder.as_markup()
    )

@file_router.message(AdminStates.waiting_file)
async def process_file_upload(message: Message, state: FSMContext):
    """
    Process file upload from admin.
    
    Args:
        message: The message object from Telegram
        state: The FSM state context
    """
    # Проверяем, есть ли файл в сообщении
    if not message.document:
        await message.answer(
            "❌ Пожалуйста, отправьте Excel-файл (.xlsx)"
        )
        return
    
    # Проверяем расширение файла
    file_name = message.document.file_name
    if not file_name.endswith('.xlsx'):
        await message.answer(
            "❌ Формат файла должен быть .xlsx"
        )
        return
    
    # Получаем данные состояния
    user_data = await state.get_data()
    language_id = user_data.get('selected_language_id')
    
    if not language_id:
        await message.answer("❌ Не выбран язык. Начните процесс заново с команды /upload")
        await state.clear()
        return
    
    # Скачиваем файл
    try:
        file = await message.bot.get_file(message.document.file_id)
        file_data = await message.bot.download_file(file.file_path)
    except Exception as e:
        logger.error(f"Error downloading file: {e}")
        await message.answer(f"❌ Ошибка при скачивании файла: {str(e)}")
        await state.clear()
        return
    
    # Сохраняем данные файла в состоянии
    await state.update_data(file_data=file_data, file_name=file_name)
    
    # Инициализируем настройки по умолчанию
    await state.update_data(
        has_headers=False, 
        clear_existing=False,
        column_number=DEFAULT_COLUMN_NUMBER,
        column_word=DEFAULT_COLUMN_WORD,
        column_transcription=DEFAULT_COLUMN_TRANSCRIPTION,
        column_translation=DEFAULT_COLUMN_TRANSLATION
    )
    
    # Устанавливаем состояние настроек загрузки
    await state.set_state(AdminStates.configuring_upload_settings)
    
    # Создаем клавиатуру с настройками загрузки файла
    builder = get_upload_settings_keyboard(
        language_id,
        column_number=DEFAULT_COLUMN_NUMBER,
        column_word=DEFAULT_COLUMN_WORD,
        column_transcription=DEFAULT_COLUMN_TRANSCRIPTION,
        column_translation=DEFAULT_COLUMN_TRANSLATION
    )
    
    # Формируем строку с текущими настройками колонок
    column_settings = (
        "Настройки колонок:\n"
        f"✅ Колонка number: {DEFAULT_COLUMN_NUMBER}\n"
        f"✅ Колонка word: {DEFAULT_COLUMN_WORD}\n"
        f"✅ Колонка transcription: {DEFAULT_COLUMN_TRANSCRIPTION}\n"
        f"✅ Колонка translation: {DEFAULT_COLUMN_TRANSLATION}\n"
    )
    
    # Предлагаем настроить параметры загрузки
    await message.answer(
        "⚙️ Настройки загрузки файла:\n\n"
        '✅ Файл содержит заголовки: "Нет"\n'
        '✅ Очистить существующие слова: "Нет"\n\n'
        f"{column_settings}\n"
        "Настройте параметры или нажмите 'Подтвердить и загрузить' для продолжения.",
        reply_markup=builder
    )

# Обработчик для состояния настроек загрузки с подтверждением
@file_router.callback_query(AdminStates.configuring_upload_settings, F.data == CallbackData.CONFIRM_UPLOAD)
async def process_upload_confirmation_from_settings(callback: CallbackQuery, state: FSMContext):
    """
    Process upload confirmation from upload settings state.
    
    Args:
        callback: The callback query from Telegram
        state: The FSM state context
    """
    logger.info("Upload confirmation from settings state")
    
    # ✅ НОВОЕ: Переходим в состояние подтверждения загрузки файла
    await state.set_state(AdminStates.confirming_file_upload)
    
    # Импортируем и вызываем обработчик подтверждения загрузки
    from app.bot.handlers.admin.file_upload.column_configuration import process_upload_confirmation
    await process_upload_confirmation(callback, state)

# ✅ НОВОЕ: Обработчик возврата в админку из настроек загрузки
@file_router.callback_query(AdminStates.configuring_upload_settings, F.data == CallbackData.BACK_TO_ADMIN)
@file_router.callback_query(AdminStates.waiting_file, F.data == CallbackData.BACK_TO_ADMIN)
async def process_back_to_admin_from_upload(callback: CallbackQuery, state: FSMContext):
    """
    Handle going back to admin menu from file upload process.
    
    Args:
        callback: The callback query from Telegram
        state: The FSM state context
    """
    logger.info("Back to admin from file upload process")
    
    # Очищаем состояние загрузки файла
    await state.clear()
    
    # Импортируем и вызываем функцию возврата в административное меню
    from app.bot.handlers.admin.admin_basic_handlers import handle_admin_mode
    await handle_admin_mode(callback, state, is_callback=True)
    
    await callback.answer()
    