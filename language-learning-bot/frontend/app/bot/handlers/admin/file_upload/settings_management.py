"""
Handlers for settings management during file upload.
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

@settings_router.callback_query(AdminStates.configuring_columns, F.data == CallbackData.TOGGLE_HEADERS)
async def toggle_headers_setting(callback: CallbackQuery, state: FSMContext):
    """
    Toggle the 'has_headers' setting.
    
    Args:
        callback: The callback query from Telegram
        state: The FSM state context
    """
    # Получаем текущие настройки
    user_data = await state.get_data()
    current_value = user_data.get('has_headers', False)
    
    # Инвертируем значение
    new_value = not current_value
    await state.update_data(has_headers=new_value)
    
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
        f"✅ Файл содержит заголовки: \"{('Да' if has_headers else 'Нет')}\"\n"
        f"✅ Очистить существующие слова: \"{('Да' if clear_existing else 'Нет')}\"\n"
        f"{column_settings_str}\n"
        "Настройте параметры, нажмите 'Настроить колонки' для настройки колонок или 'Подтвердить и загрузить' для загрузки файла.",
        reply_markup=builder.as_markup()
    )
    
    await callback.answer()

@settings_router.callback_query(AdminStates.configuring_columns, F.data == CallbackData.TOGGLE_CLEAR_EXISTING)
async def toggle_clear_existing_setting(callback: CallbackQuery, state: FSMContext):
    """
    Toggle the 'clear_existing' setting.
    
    Args:
        callback: The callback query from Telegram
        state: The FSM state context
    """
    # Получаем текущие настройки
    user_data = await state.get_data()
    current_value = user_data.get('clear_existing', False)
    
    # Инвертируем значение
    new_value = not current_value
    await state.update_data(clear_existing=new_value)
    
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
        callback_data="toggle_headers"
    ))
    builder.add(InlineKeyboardButton(
        text=clear_btn_text, 
        callback_data="toggle_clear_existing"
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
        callback_data="confirm_upload"
    ))
    
    builder.add(InlineKeyboardButton(
        text="⬅️ Отмена", 
        callback_data="back_to_admin"
    ))
    builder.adjust(1)
    
    await callback.message.edit_text(
        "⚙️ Настройки загрузки файла:\n\n"
        f"✅ Файл содержит заголовки: \"{('Да' if has_headers else 'Нет')}\"\n"
        f"✅ Очистить существующие слова: \"{('Да' if clear_existing else 'Нет')}\"\n"
        f"{column_settings_str}\n"
        "Настройте параметры, нажмите 'Настроить колонки' для настройки колонок или 'Подтвердить и загрузить' для загрузки файла.",
        reply_markup=builder.as_markup()
    )
    
    await callback.answer()

@settings_router.callback_query(AdminStates.configuring_columns, F.data == CallbackData.BACK_TO_SETTINGS)
async def process_back_to_settings(callback: CallbackQuery, state: FSMContext):
    """
    Handle going back to file settings screen.
    
    Args:
        callback: The callback query from Telegram
        state: The FSM state context
    """
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
        callback_data="toggle_headers"
    ))
    builder.add(InlineKeyboardButton(
        text=clear_btn_text, 
        callback_data="toggle_clear_existing"
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
        callback_data="confirm_upload"
    ))
    
    builder.add(InlineKeyboardButton(
        text="⬅️ Отмена", 
        callback_data="back_to_admin"
    ))
    builder.adjust(1)
    
    await callback.message.edit_text(
        "⚙️ Настройки загрузки файла:\n\n"
        f"✅ Файл содержит заголовки: \"{('Да' if has_headers else 'Нет')}\"\n"
        f"✅ Очистить существующие слова: \"{('Да' if clear_existing else 'Нет')}\"\n"
        f"{column_settings_str}\n"
        "Настройте параметры, нажмите 'Настроить колонки' для настройки колонок или 'Подтвердить и загрузить' для загрузки файла.",
        reply_markup=builder.as_markup()
    )
    
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
    for col_type in ["number", "word", "transcription", "translation"]:
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
    for col_type in ["number", "word", "transcription", "translation"]:
        col_value = user_data.get(f"column_{col_type}")
        if col_value is not None:
            column_values.append(str(col_value))
    
    # Если есть настройки колонок, добавляем их в текст кнопки
    if column_values:
        return f"(сейчас: {', '.join(column_values)})"
    
    return ""