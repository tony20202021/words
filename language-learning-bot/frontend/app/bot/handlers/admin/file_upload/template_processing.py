"""
Handlers for template processing during file upload.
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

# Создаем роутер для обработчиков шаблонов колонок
template_router = Router()

@template_router.callback_query(AdminStates.configuring_columns, F.data.startswith("upload_columns:"))
@template_router.callback_query(AdminStates.configuring_upload_settings, F.data.startswith("upload_columns:"))
@template_router.callback_query(AdminStates.selecting_column_template, F.data.startswith("upload_columns:"))
async def process_column_template(callback: CallbackQuery, state: FSMContext):
    """
    Process predefined column template selection.
    
    Args:
        callback: The callback query from Telegram
        state: The FSM state context
    """
    # Извлекаем данные из callback_data
    parts = callback.data.split(":")
    column_indices = parts[1].split(",")
    language_id = parts[2]
    
    logger.info(f"Selected column template: {column_indices} for language ID: {language_id}")
    
    # ✅ НОВОЕ: Устанавливаем состояние выбора шаблона колонок
    await state.set_state(AdminStates.selecting_column_template)
    
    # Преобразуем индексы из строк в целые числа
    try:
        column_number = int(column_indices[0])
        column_word = int(column_indices[1])
        column_transcription = int(column_indices[2])
        column_translation = int(column_indices[3])
    except (IndexError, ValueError) as e:
        logger.error(f"Error parsing column template: {e}")
        await callback.message.answer("❌ Ошибка при обработке шаблона колонок. Попробуйте настроить вручную.")
        # ✅ НОВОЕ: При ошибке возвращаемся к настройкам загрузки
        await state.set_state(AdminStates.configuring_upload_settings)
        await callback.answer()
        return
    
    # Сохраняем выбранные колонки в состоянии
    await state.update_data({
        "column_number": column_number,
        "column_word": column_word,
        "column_transcription": column_transcription,
        "column_translation": column_translation
    })
    
    # Выводим информацию о выбранном шаблоне
    template_info = (
        f"✅ Выбран шаблон:\n"
        f"- Колонка номера: {column_number}\n"
        f"- Колонка слова: {column_word}\n"
        f"- Колонка транскрипции: {column_transcription}\n"
        f"- Колонка перевода: {column_translation}\n\n"
        f"Теперь можно загрузить файл или настроить колонки точнее."
    )
    
    # Создаем клавиатуру с кнопкой подтверждения и опцией ручной настройки
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(
        text="✅ Загрузить файл с этими настройками",
        callback_data=CallbackData.CONFIRM_UPLOAD
    ))
    builder.add(InlineKeyboardButton(
        text="🔧 Настроить колонки вручную",
        callback_data=f"{CallbackData.SELECT_COLUMN_TYPE}:{language_id}"
    ))
    builder.add(InlineKeyboardButton(
        text="⬅️ Назад к настройкам",
        callback_data=CallbackData.BACK_TO_SETTINGS
    ))
    builder.adjust(1)  # По одной кнопке в строке
    
    await callback.message.edit_text(
        template_info,
        reply_markup=builder.as_markup()
    )
    
    await callback.answer()

# ✅ НОВОЕ: Обработчик подтверждения загрузки из состояния выбора шаблона
@template_router.callback_query(AdminStates.selecting_column_template, F.data == CallbackData.CONFIRM_UPLOAD)
async def process_upload_confirmation_from_template(callback: CallbackQuery, state: FSMContext):
    """
    Process upload confirmation from template selection state.
    
    Args:
        callback: The callback query from Telegram
        state: The FSM state context
    """
    logger.info("Upload confirmation from template selection")
    
    # ✅ НОВОЕ: Переходим в состояние подтверждения загрузки файла
    await state.set_state(AdminStates.confirming_file_upload)
    
    # Импортируем и вызываем обработчик подтверждения загрузки
    from app.bot.handlers.admin.file_upload.column_configuration import process_upload_confirmation
    await process_upload_confirmation(callback, state)

# ✅ НОВОЕ: Обработчик возврата к настройкам из шаблона
@template_router.callback_query(AdminStates.selecting_column_template, F.data == CallbackData.BACK_TO_SETTINGS)
async def process_back_to_settings_from_template(callback: CallbackQuery, state: FSMContext):
    """
    Handle going back to settings from template selection.
    
    Args:
        callback: The callback query from Telegram
        state: The FSM state context
    """
    logger.info("Back to settings from template selection")
    
    # ✅ НОВОЕ: Возвращаемся к состоянию настроек загрузки
    await state.set_state(AdminStates.configuring_upload_settings)
    
    # Импортируем и вызываем обработчик возврата к настройкам
    from app.bot.handlers.admin.file_upload.settings_management import process_back_to_settings
    await process_back_to_settings(callback, state)

# ✅ НОВОЕ: Обработчик настройки колонок из шаблона
@template_router.callback_query(AdminStates.selecting_column_template, F.data.startswith(CallbackData.SELECT_COLUMN_TYPE))
async def process_configure_columns_from_template(callback: CallbackQuery, state: FSMContext):
    """
    Handle configuring columns manually from template selection.
    
    Args:
        callback: The callback query from Telegram
        state: The FSM state context
    """
    logger.info("Configure columns manually from template selection")
    
    # ✅ НОВОЕ: Переходим к состоянию конфигурации колонок
    await state.set_state(AdminStates.configuring_columns)
    
    # Импортируем и вызываем обработчик выбора типа колонки
    from app.bot.handlers.admin.file_upload.column_type_processing import process_select_column_type
    await process_select_column_type(callback, state)

# ✅ НОВОЕ: Обработчик возврата в админку из шаблона
@template_router.callback_query(AdminStates.selecting_column_template, F.data == CallbackData.BACK_TO_ADMIN)
async def process_back_to_admin_from_template(callback: CallbackQuery, state: FSMContext):
    """
    Handle going back to admin menu from template selection.
    
    Args:
        callback: The callback query from Telegram
        state: The FSM state context
    """
    logger.info("Back to admin from template selection")
    
    # Очищаем состояние загрузки файла
    await state.clear()
    
    # Импортируем и вызываем функцию возврата в административное меню
    from app.bot.handlers.admin.admin_basic_handlers import handle_admin_mode
    await handle_admin_mode(callback, state, is_callback=True)
    
    await callback.answer()

# ✅ НОВОЕ: Предопределенные шаблоны колонок
COLUMN_TEMPLATES = {
    "1": {
        "name": "Номер, слово, транскрипция, перевод",
        "columns": [0, 1, 2, 3],
        "description": "Стандартный порядок: номер слова в первой колонке, слово во второй, транскрипция в третьей, перевод в четвертой"
    },
    "2": {
        "name": "Номер, перевод, слово, транскрипция", 
        "columns": [0, 2, 1, 3],
        "description": "Альтернативный порядок: номер, затем перевод на русском, затем слово и транскрипция"
    },
    "3": {
        "name": "Слово, транскрипция, перевод, номер",
        "columns": [3, 0, 1, 2], 
        "description": "Порядок для словарей: слово в первой колонке, транскрипция во второй, перевод в третьей, номер в четвертой"
    },
    "4": {
        "name": "Только слово и перевод",
        "columns": [None, 0, None, 1],
        "description": "Минимальный набор: только слово и перевод без номера и транскрипции"
    }
}

def get_template_by_id(template_id: str) -> dict:
    """
    Get template configuration by ID.
    
    Args:
        template_id: Template identifier
        
    Returns:
        dict: Template configuration or None if not found
    """
    return COLUMN_TEMPLATES.get(template_id)

def create_template_selection_keyboard(language_id: str) -> InlineKeyboardButton:
    """
    Create keyboard for template selection.
    
    Args:
        language_id: ID of the target language
        
    Returns:
        InlineKeyboardMarkup: Template selection keyboard
    """
    builder = InlineKeyboardBuilder()
    
    # Добавляем предопределенные шаблоны
    for template_id, template_config in COLUMN_TEMPLATES.items():
        columns = template_config["columns"]
        # Формируем callback_data для шаблона
        columns_str = ",".join([str(col) if col is not None else "0" for col in columns])
        callback_data = f"upload_columns:{columns_str}:{language_id}"
        
        builder.add(InlineKeyboardButton(
            text=f"{template_id}️⃣ {template_config['name']}", 
            callback_data=callback_data
        ))
    
    # Добавляем кнопку для ручной настройки
    builder.add(InlineKeyboardButton(
        text="🔧 Настроить вручную", 
        callback_data=f"{CallbackData.SELECT_COLUMN_TYPE}:{language_id}"
    ))
    
    # Добавляем кнопку отмены
    builder.add(InlineKeyboardButton(
        text="⬅️ Назад к настройкам", 
        callback_data=CallbackData.BACK_TO_SETTINGS
    ))
    
    builder.adjust(1)  # По одной кнопке в строке
    return builder.as_markup()

# ✅ НОВОЕ: Обработчик для отображения списка шаблонов
@template_router.callback_query(AdminStates.configuring_upload_settings, F.data == "show_column_templates")
@template_router.callback_query(AdminStates.configuring_columns, F.data == "show_column_templates")
async def process_show_column_templates(callback: CallbackQuery, state: FSMContext):
    """
    Show available column templates.
    
    Args:
        callback: The callback query from Telegram
        state: The FSM state context
    """
    logger.info("Showing column templates")
    
    # ✅ НОВОЕ: Устанавливаем состояние выбора шаблона колонок
    await state.set_state(AdminStates.selecting_column_template)
    
    # Получаем ID языка из состояния
    user_data = await state.get_data()
    language_id = user_data.get('selected_language_id')
    
    if not language_id:
        await callback.message.answer("❌ Ошибка: язык не выбран")
        await state.set_state(AdminStates.configuring_upload_settings)
        await callback.answer()
        return
    
    # Создаем клавиатуру с шаблонами
    keyboard = create_template_selection_keyboard(language_id)
    
    # Формируем текст с описанием шаблонов
    templates_text = "📋 Выберите шаблон расположения колонок:\n\n"
    
    for template_id, template_config in COLUMN_TEMPLATES.items():
        templates_text += f"{template_id}️⃣ <b>{template_config['name']}</b>\n"
        templates_text += f"   {template_config['description']}\n\n"
    
    templates_text += "Или настройте колонки вручную для максимального контроля."
    
    await callback.message.edit_text(
        templates_text,
        parse_mode="HTML",
        reply_markup=keyboard
    )
    
    await callback.answer()
    