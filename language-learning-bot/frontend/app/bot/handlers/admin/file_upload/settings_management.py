"""
Handlers for settings management during file upload.
Updated with FSM states for better navigation control.
"""

from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
from app.utils.logger import setup_logger
from app.bot.states.centralized_states import AdminStates
from app.utils.callback_constants import CallbackData

logger = setup_logger(__name__)

# Создаем роутер для обработчиков управления настройками
settings_router = Router()

@settings_router.callback_query(AdminStates.configuring_upload_settings, F.data == CallbackData.TOGGLE_HEADERS)
@settings_router.callback_query(AdminStates.configuring_columns, F.data == CallbackData.TOGGLE_HEADERS)
async def toggle_headers_setting(callback: CallbackQuery, state: FSMContext):
    """
    Toggle the 'has_headers' setting.
    
    Args:
        callback: The callback query from Telegram
        state: The FSM state context
    """
    logger.info("Toggling headers setting")
    
    # Получаем текущие настройки
    user_data = await state.get_data()
    current_value = user_data.get('has_headers', False)
    
    # Инвертируем значение
    new_value = not current_value
    await state.update_data(has_headers=new_value)
    
    # ✅ НОВОЕ: Убеждаемся, что мы в правильном состоянии
    current_state = await state.get_state()
    if current_state != AdminStates.configuring_columns.state:
        await state.set_state(AdminStates.configuring_upload_settings)
    
    # Получаем обновленные данные
    user_data = await state.get_data()
    has_headers = user_data.get('has_headers', False)
    clear_existing = user_data.get('clear_existing', False)
    
    # Формируем строку с текущими настройками колонок, если они есть
    column_settings_str = format_column_settings(user_data)
    
    # Тексты для кнопок (без использования f-строк с экранированными кавычками)
    headers_btn_text = "📝 Файл содержит заголовки: поменять на \"Нет\"" if has_headers else "📝 Файл содержит заголовки: поменять на \"Да\""
    clear_btn_text = "🗑️ Очистить существующие слова: поменять на \"Нет\"" if clear_existing else "🗑️ Очистить существующие слова: поменять на \"Да\""
    
    # Обновляем сообщение
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(
        text=headers_btn_text, 
        callback_data=CallbackData.TOGGLE_HEADERS
    ))
    builder.add(InlineKeyboardButton(
        text=clear_btn_text, 
        callback_data=CallbackData.TOGGLE_CLEAR_EXISTING
    ))
    
    # Добавляем информацию о текущих настройках колонок в кнопку
    language_id = user_data.get('selected_language_id')
    column_info = get_column_info_text(user_data)
    builder.add(InlineKeyboardButton(
        text=f"🔧 Настроить колонки {column_info}", 
        callback_data=f"{CallbackData.SELECT_COLUMN_TYPE}:{language_id}"
    ))
    
    # Добавляем кнопку подтверждения загрузки
    builder.add(InlineKeyboardButton(
        text="✅ Подтвердить и загрузить", 
        callback_data=CallbackData.CONFIRM_UPLOAD
    ))
    
    builder.add(InlineKeyboardButton(
        text="⬅️ Отмена", 
        callback_data=CallbackData.BACK_TO_ADMIN 
        # TODO - по этой кнопке происходит переход на экран "Панель администратора Выберите действие:", без никакой доп информации
        # надо переходить на экран "Режим администратора активирован!" со всей заполненной инфой
    ))
    builder.adjust(1)
    
    # TODO  кажется этот текст дублируется в 2 разных местах
    # найти и вынести в общую функцию
    await callback.message.edit_text(
        "⚙️ Настройки загрузки файла:\n\n"
        f"{('✅' if has_headers else '❌')} Файл содержит заголовки: \"{('Да' if has_headers else 'Нет')}\"\n"
        f"{('✅' if clear_existing else '❌')} Очистить существующие слова: \"{('Да' if clear_existing else 'Нет')}\"\n\n"
        f"{column_settings_str}\n"
        "Настройте параметры, нажмите 'Настроить колонки' для настройки колонок или 'Подтвердить и загрузить' для загрузки файла.",
        reply_markup=builder.as_markup()
    )
    
    await callback.answer()

@settings_router.callback_query(AdminStates.configuring_upload_settings, F.data == CallbackData.TOGGLE_CLEAR_EXISTING)
@settings_router.callback_query(AdminStates.configuring_columns, F.data == CallbackData.TOGGLE_CLEAR_EXISTING)
async def toggle_clear_existing_setting(callback: CallbackQuery, state: FSMContext):
    """
    Toggle the 'clear_existing' setting.
    
    Args:
        callback: The callback query from Telegram
        state: The FSM state context
    """
    logger.info("Toggling clear existing setting")
    
    # Получаем текущие настройки
    user_data = await state.get_data()
    current_value = user_data.get('clear_existing', False)
    
    # Инвертируем значение
    new_value = not current_value
    await state.update_data(clear_existing=new_value)
    
    # ✅ НОВОЕ: Убеждаемся, что мы в правильном состоянии
    current_state = await state.get_state()
    if current_state != AdminStates.configuring_columns.state:
        await state.set_state(AdminStates.configuring_upload_settings)
    
    # Получаем обновленные данные
    user_data = await state.get_data()
    has_headers = user_data.get('has_headers', False)
    clear_existing = user_data.get('clear_existing', False)
    
    # Формируем строку с текущими настройками колонок, если они есть
    column_settings_str = format_column_settings(user_data)
    
    # Тексты для кнопок (без использования f-строк с экранированными кавычками)
    headers_btn_text = "📝 Файл содержит заголовки: поменять на \"Нет\"" if has_headers else "📝 Файл содержит заголовки: поменять на \"Да\""
    clear_btn_text = "🗑️ Очистить существующие слова: поменять на \"Нет\"" if clear_existing else "🗑️ Очистить существующие слова: поmenять на \"Да\""
    
    # Обновляем сообщение
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(
        text=headers_btn_text, 
        callback_data=CallbackData.TOGGLE_HEADERS
    ))
    builder.add(InlineKeyboardButton(
        text=clear_btn_text, 
        callback_data=CallbackData.TOGGLE_CLEAR_EXISTING
    ))
    
    # Добавляем информацию о текущих настройках колонок в кнопку
    language_id = user_data.get('selected_language_id')
    column_info = get_column_info_text(user_data)
    builder.add(InlineKeyboardButton(
        text=f"🔧 Настроить колонки {column_info}", 
        callback_data=f"{CallbackData.SELECT_COLUMN_TYPE}:{language_id}"
    ))
    
    # Добавляем кнопку подтверждения загрузки
    builder.add(InlineKeyboardButton(
        text="✅ Подтвердить и загрузить", 
        callback_data=CallbackData.CONFIRM_UPLOAD
    ))
    
    builder.add(InlineKeyboardButton(
        text="⬅️ Отмена", 
        callback_data=CallbackData.BACK_TO_ADMIN
    ))
    builder.adjust(1)
    
    await callback.message.edit_text(
        "⚙️ Настройки загрузки файла:\n\n"
        f"{('✅' if has_headers else '❌')} Файл содержит заголовки: \"{('Да' if has_headers else 'Нет')}\"\n"
        f"{('✅' if clear_existing else '❌')} Очистить существующие слова: \"{('Да' if clear_existing else 'Нет')}\"\n\n"
        f"{column_settings_str}\n"
        "Настройте параметры, нажмите 'Настроить колонки' для настройки колонок или 'Подтвердить и загрузить' для загрузки файла.",
        reply_markup=builder.as_markup()
    )
    
    await callback.answer()

@settings_router.callback_query(AdminStates.configuring_upload_settings, F.data == CallbackData.BACK_TO_SETTINGS)
@settings_router.callback_query(AdminStates.configuring_columns, F.data == CallbackData.BACK_TO_SETTINGS)
async def process_back_to_settings(callback: CallbackQuery, state: FSMContext):
    """
    Handle going back to file settings screen.
    
    Args:
        callback: The callback query from Telegram
        state: The FSM state context
    """
    logger.info("Back to upload settings")
    
    # ✅ НОВОЕ: Устанавливаем состояние настроек загрузки
    await state.set_state(AdminStates.configuring_upload_settings)
    
    # Получаем данные состояния
    user_data = await state.get_data()
    has_headers = user_data.get('has_headers', False)
    clear_existing = user_data.get('clear_existing', False)
    
    # Формируем строку с текущими настройками колонок, если они есть
    column_settings_str = format_column_settings(user_data)
    
    # Тексты для кнопок (без использования f-строк с экранированными кавычками)
    headers_btn_text = "📝 Файл содержит заголовки: поменять на \"Нет\"" if has_headers else "📝 Файл содержит заголовки: поменять на \"Да\""
    clear_btn_text = "🗑️ Очистить существующие слова: поменять на \"Нет\"" if clear_existing else "🗑️ Очистить существующие слова: поменять на \"Да\""
    
    # Обновляем сообщение
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(
        text=headers_btn_text, 
        callback_data=CallbackData.TOGGLE_HEADERS
    ))
    builder.add(InlineKeyboardButton(
        text=clear_btn_text, 
        callback_data=CallbackData.TOGGLE_CLEAR_EXISTING
    ))
    
    # Добавляем информацию о текущих настройках колонок в кнопку
    language_id = user_data.get('selected_language_id')
    column_info = get_column_info_text(user_data)
    builder.add(InlineKeyboardButton(
        text=f"🔧 Настроить колонки {column_info}", 
        callback_data=f"{CallbackData.SELECT_COLUMN_TYPE}:{language_id}"
    ))
    
    # Добавляем кнопку подтверждения загрузки
    builder.add(InlineKeyboardButton(
        text="✅ Подтвердить и загрузить", 
        callback_data=CallbackData.CONFIRM_UPLOAD
    ))
    
    builder.add(InlineKeyboardButton(
        text="⬅️ Отмена", 
        callback_data=CallbackData.BACK_TO_ADMIN
    ))
    builder.adjust(1)
    
    await callback.message.edit_text(
        "⚙️ Настройки загрузки файла:\n\n"
        f"{('✅' if has_headers else '❌')} Файл содержит заголовки: \"{('Да' if has_headers else 'Нет')}\"\n"
        f"{('✅' if clear_existing else '❌')} Очистить существующие слова: \"{('Да' if clear_existing else 'Нет')}\"\n\n"
        f"{column_settings_str}\n"
        "Настройте параметры, нажмите 'Настроить колонки' для настройки колонок или 'Подтвердить и загрузить' для загрузки файла.",
        reply_markup=builder.as_markup()
    )
    
    await callback.answer()

# ✅ НОВОЕ: Обработчик возврата в админку из настроек загрузки
@settings_router.callback_query(AdminStates.configuring_upload_settings, F.data == CallbackData.BACK_TO_ADMIN)
async def process_back_to_admin_from_settings(callback: CallbackQuery, state: FSMContext):
    """
    Handle going back to admin menu from upload settings.
    
    Args:
        callback: The callback query from Telegram
        state: The FSM state context
    """
    logger.info("Back to admin from upload settings")
    
    # Очищаем состояние загрузки файла
    await state.clear()
    
    # Импортируем и вызываем функцию возврата в административное меню
    from app.bot.handlers.admin.admin_basic_handlers import handle_admin_mode
    await handle_admin_mode(callback, state, is_callback=True)
    
    await callback.answer()

def format_column_settings(user_data):
    """
    Форматирует настройки колонок для отображения в сообщении.
    
    Args:
        user_data: Данные состояния пользователя
        
    Returns:
        str: Форматированная строка с настройками колонок
    """
    # Проверяем, есть ли настройки колонок
    column_settings = []
    for col_type in ["number", "word", "transcription", "translation", "radicals", "references", "tones"]:
        col_key = f"column_{col_type}"
        col_value = user_data.get(col_key)
        if col_value is not None:
            column_settings.append(f"✅ {col_key.replace('column_', 'Колонка ')}: {col_value}")
    
    # Если нет настроенных колонок, возвращаем пустую строку
    if not column_settings:
        return ""
    
    # Возвращаем отформатированную строку
    return "Настройки колонок:\n" + "\n".join(column_settings) + "\n"

def get_column_info_text(user_data):
    """
    Получает текст с информацией о настроенных колонках для кнопки.
    
    Args:
        user_data: Данные состояния пользователя
        
    Returns:
        str: Текст с информацией о колонках
    """
    # Проверяем наличие настроек колонок
    column_values = []
    for col_type in ["number", "word", "transcription", "translation", "radicals", "references", "tones"]:
        col_value = user_data.get(f"column_{col_type}")
        if col_value is not None:
            column_values.append(str(col_value))
    
    # Если есть настройки колонок, добавляем их в текст кнопки
    if column_values:
        return f"(сейчас: {', '.join(column_values)})"
    
    return ""

# ✅ НОВОЕ: Функция для создания общего интерфейса настроек загрузки
def create_upload_settings_interface(user_data: dict) -> tuple:
    """
    Создает интерфейс настроек загрузки файла.
    
    Args:
        user_data: Данные состояния пользователя
        
    Returns:
        tuple: (message_text, keyboard_markup)
    """
    has_headers = user_data.get('has_headers', False)
    clear_existing = user_data.get('clear_existing', False)
    language_id = user_data.get('selected_language_id')
    
    # Формируем строку с текущими настройками колонок
    column_settings_str = format_column_settings(user_data)
    
    # Тексты для кнопок
    headers_btn_text = "📝 Файл содержит заголовки: поменять на \"Нет\"" if has_headers else "📝 Файл содержит заголовки: поменять на \"Да\""
    clear_btn_text = "🗑️ Очистить существующие слова: поменять на \"Нет\"" if clear_existing else "🗑️ Очистить существующие слова: поменять на \"Да\""
    
    # Создаем клавиатуру
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(
        text=headers_btn_text, 
        callback_data=CallbackData.TOGGLE_HEADERS
    ))
    builder.add(InlineKeyboardButton(
        text=clear_btn_text, 
        callback_data=CallbackData.TOGGLE_CLEAR_EXISTING
    ))
    
    # Добавляем информацию о настройках колонок в кнопку
    column_info = get_column_info_text(user_data)
    builder.add(InlineKeyboardButton(
        text=f"🔧 Настроить колонки {column_info}", 
        callback_data=f"{CallbackData.SELECT_COLUMN_TYPE}:{language_id}"
    ))
    
    # Добавляем кнопку подтверждения загрузки
    builder.add(InlineKeyboardButton(
        text="✅ Подтвердить и загрузить", 
        callback_data=CallbackData.CONFIRM_UPLOAD
    ))
    
    builder.add(InlineKeyboardButton(
        text="⬅️ Отмена", 
        callback_data=CallbackData.BACK_TO_ADMIN
    ))
    builder.adjust(1)
    
    # Создаем текст сообщения
    message_text = (
        "⚙️ Настройки загрузки файла:\n\n"
        f"✅ Файл содержит заголовки: \"{('Да' if has_headers else 'Нет')}\"\n"
        f"✅ Очистить существующие слова: \"{('Да' if clear_existing else 'Нет')}\"\n\n"
        f"{column_settings_str}\n"
        "Настройте параметры, нажмите 'Настроить колонки' для настройки колонок или 'Подтвердить и загрузить' для загрузки файла."
    )
    
    return message_text, builder.as_markup()
