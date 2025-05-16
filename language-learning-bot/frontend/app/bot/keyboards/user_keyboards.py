"""
Keyboards for user
"""

from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

def create_settings_keyboard(skip_marked, use_check_date, show_hints=True, show_debug=False):
    """
    Create keyboard for settings menu.
    
    Args:
        skip_marked: Whether to skip marked words
        use_check_date: Whether to use check date
        show_hints: Whether to show hint buttons
        show_debug: Whether to show debug information
        
    Returns:
        InlineKeyboardMarkup: Settings keyboard markup
    """
    # Создаем билдер для клавиатуры
    builder = InlineKeyboardBuilder()
    
    # Добавляем кнопки
    builder.add(InlineKeyboardButton(
        text="🔢 Изменить начальное слово",
        callback_data="settings_start_word"
    ))
    
    builder.add(InlineKeyboardButton(
        text=f"⏩ Помеченные слова: сменить на \"{'Показывать' if skip_marked else 'Пропускать'}\"",
        callback_data="settings_toggle_skip_marked"
    ))

    builder.add(InlineKeyboardButton(
        text=f"📅 Период проверки: сменить на \"{'Не учитывать' if use_check_date else 'Учитывать'}\"",
        callback_data="settings_toggle_check_date"
    ))
    
    builder.add(InlineKeyboardButton(
        text=f"💡 Подсказки: сменить на \"{'Пропускать' if show_hints else 'Придумывать'}\"",
        callback_data="settings_toggle_show_hints"
    ))
    
    # Добавляем новую кнопку для отладочной информации
    builder.add(InlineKeyboardButton(
        text=f"🔍 Отладочная информация: сменить на \"{'Скрывать' if show_debug else 'Показывать'}\"",
        callback_data="settings_toggle_show_debug"
    ))
    
    # Настраиваем ширину строки клавиатуры (по 1 кнопке в ряд)
    builder.adjust(1)
    
    return builder.as_markup()