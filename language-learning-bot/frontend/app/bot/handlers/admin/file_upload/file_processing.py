"""
Handlers for file upload processing.
"""

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardButton, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
from app.utils.api_utils import get_api_client_from_bot
from app.utils.logger import setup_logger
from app.bot.handlers.admin.admin_states import AdminStates

logger = setup_logger(__name__)

# Создаем роутер для обработчиков загрузки файла
file_router = Router()

# TODO добавить параметр - очистить статистику всех пользователей по этому языку
# реализовать как отдельную функцию clien API
# и добавить  вызов этой функции (очистить статистику всех пользователей по выбранному языку) - в админ/управление языком
# сделать нужные изменения в client API, backend


# TODO сейчас на длинных файлах - выдается сообщение об ожидании
# и потом ошибка, в логах фронтенда - сообщение о тайм-ауте
# сделать чтобы фронтенд не зависал в ответе
# отправить сообщение "ожидайте результата"
# ждать окончания загрузки на бэкенд
# после окончания - отправить новое сообщение, что все завершено

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
    
    # Получаем клиент API с помощью утилиты
    api_client = get_api_client_from_bot(message.bot)
    
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
    
    # Получаем обновленные данные состояния
    user_data = await state.get_data()
    
    # Создаем клавиатуру с настройками загрузки файла
    builder = InlineKeyboardBuilder()
    
    # Кнопки для настройки файла
    builder.add(InlineKeyboardButton(
        text='📝 Файл содержит заголовки: поменять на "Да"', 
        callback_data="toggle_headers"
    ))
    builder.add(InlineKeyboardButton(
        text='🗑️ Очистить существующие слова: поменять на "Да"', 
        callback_data="toggle_clear_existing"
    ))
    
    # Добавляем информацию о текущих настройках колонок в кнопку
    column_info = f"(сейчас: {DEFAULT_COLUMN_NUMBER}, {DEFAULT_COLUMN_WORD}, {DEFAULT_COLUMN_TRANSCRIPTION}, {DEFAULT_COLUMN_TRANSLATION})"
    builder.add(InlineKeyboardButton(
        text=f"🔧 Настроить колонки {column_info}", 
        callback_data=f"select_column_type:{language_id}"
    ))
    
    # Добавляем кнопку подтверждения загрузки
    builder.add(InlineKeyboardButton(
        text="✅ Подтвердить и загрузить", 
        callback_data="confirm_upload"
    ))
    
    builder.add(InlineKeyboardButton(
        text="⬅️ Отмена", 
        callback_data="back_to_admin"
    ))
    
    # Настраиваем ширину строки клавиатуры (по 1 кнопке в ряд)
    builder.adjust(1)
    
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
        reply_markup=builder.as_markup()
    )
    
    # Переходим в состояние настройки параметров
    await state.set_state(AdminStates.configuring_columns)