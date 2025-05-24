"""
Handlers for template processing during file upload.
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
    
    # Преобразуем индексы из строк в целые числа
    try:
        column_number = int(column_indices[0])
        column_word = int(column_indices[1])
        column_transcription = int(column_indices[2])
        column_translation = int(column_indices[3])
    except (IndexError, ValueError) as e:
        logger.error(f"Error parsing column template: {e}")
        await callback.message.answer("❌ Ошибка при обработке шаблона колонок. Попробуйте настроить вручную.")
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
        callback_data="confirm_upload"
    ))
    builder.add(InlineKeyboardButton(
        text="🔧 Настроить колонки вручную",
        callback_data=f"{CallbackData.SELECT_COLUMN_TYPE}:{language_id}"
    ))
    builder.add(InlineKeyboardButton(
        text="⬅️ Назад к настройкам",
        callback_data="back_to_settings"
    ))
    builder.adjust(1)  # По одной кнопке в строке
    
    await callback.message.edit_text(
        template_info,
        reply_markup=builder.as_markup()
    )
    
    await callback.answer()

