"""
Keyboards for admin
"""

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def get_admin_keyboard() -> InlineKeyboardMarkup:
    """
    Создает клавиатуру для меню администратора.
    
    Returns:
        InlineKeyboardMarkup: Клавиатура с кнопками администратора
    """
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👨‍💼 Управление языками", callback_data="admin_languages")],
        [InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats_callback")],
        [InlineKeyboardButton(text="⬅️ Выйти из режима администратора", callback_data="back_to_start")]
    ])
    return keyboard


def get_languages_keyboard(languages: list) -> InlineKeyboardMarkup:
    """
    Создает клавиатуру для списка языков.
    
    Args:
        languages (list): Список языков
        
    Returns:
        InlineKeyboardMarkup: Клавиатура с кнопками языков
    """
    keyboard = InlineKeyboardMarkup(inline_keyboard=[])
    
    # Кнопки для языков - меняем формат с двоеточия на подчеркивание
    for language in languages:
        lang_id = language.get('_id', language.get('id'))
        keyboard.inline_keyboard.append([
            InlineKeyboardButton(
                text=f"{language['name_ru']} ({language['name_foreign']})", 
                callback_data=f"edit_language_{lang_id}"
            )
        ])
    
    # Кнопка для создания нового языка
    keyboard.inline_keyboard.append([
        InlineKeyboardButton(text="➕ Создать новый язык", callback_data="create_language")
    ])
    
    # Кнопка возврата
    keyboard.inline_keyboard.append([
        InlineKeyboardButton(text="⬅️ Вернуться к администрированию", callback_data="back_to_admin")
    ])
    
    return keyboard


def get_edit_language_keyboard(language_id: str) -> InlineKeyboardMarkup:
    """
    Создает клавиатуру для редактирования языка.
    
    Args:
        language_id (str): ID языка
        
    Returns:
        InlineKeyboardMarkup: Клавиатура с кнопками для редактирования языка
    """
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✏️ Изменить русское название", callback_data=f"edit_name_ru_{language_id}")],
        [InlineKeyboardButton(text="✏️ Изменить оригинальное название", callback_data=f"edit_name_foreign_{language_id}")],
        [InlineKeyboardButton(text="📤 Загрузить файл со словами", callback_data=f"upload_to_lang_{language_id}")],
        [InlineKeyboardButton(text="🔍 Найти слово по номеру", callback_data=f"search_word_by_number_{language_id}")],
        [InlineKeyboardButton(text="🗑️ Удалить язык", callback_data=f"delete_language_{language_id}")],
        [InlineKeyboardButton(text="⬅️ Назад к языкам", callback_data="back_to_languages")]
    ])
    
    return keyboard


def get_back_to_languages_keyboard() -> InlineKeyboardMarkup:
    """
    Создает клавиатуру с кнопкой возврата к списку языков.
    
    Returns:
        InlineKeyboardMarkup: Клавиатура с кнопкой возврата
    """
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Назад к списку языков", callback_data="back_to_languages")]
    ])
    return keyboard


def get_back_to_admin_keyboard() -> InlineKeyboardMarkup:
    """
    Создает клавиатуру с кнопкой возврата к меню администратора.
    
    Returns:
        InlineKeyboardMarkup: Клавиатура с кнопкой возврата
    """
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Назад к меню администратора", callback_data="back_to_admin")]
    ])
    return keyboard


def get_yes_no_keyboard(action: str, entity_id: str) -> InlineKeyboardMarkup:
    """
    Создает клавиатуру с кнопками "Да" и "Нет" для подтверждения действия.
    
    Args:
        action (str): Тип действия (например, "delete_language")
        entity_id (str): ID сущности, над которой выполняется действие
        
    Returns:
        InlineKeyboardMarkup: Клавиатура с кнопками "Да" и "Нет"
    """
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Да", callback_data=f"confirm_{action}_{entity_id}"),
            InlineKeyboardButton(text="❌ Нет", callback_data=f"cancel_{action}_{entity_id}")
        ]
    ])
    return keyboard


def get_upload_columns_keyboard(language_id: str) -> InlineKeyboardMarkup:
    """
    Создает клавиатуру для настройки колонок при загрузке файла.
    
    Args:
        language_id (str): ID языка
        
    Returns:
        InlineKeyboardMarkup: Клавиатура с кнопками настройки колонок
    """
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="1️⃣ Номер, слово, транскрипция, перевод", 
                             callback_data=f"column_template_1_{language_id}")],
        [InlineKeyboardButton(text="2️⃣ Номер, перевод, слово, транскрипция", 
                             callback_data=f"column_template_2_{language_id}")],
        [InlineKeyboardButton(text="3️⃣ Слово, транскрипция, перевод, номер", 
                             callback_data=f"column_template_3_{language_id}")],
        [InlineKeyboardButton(text="4️⃣ Настроить порядок вручную", 
                             callback_data=f"custom_columns_{language_id}")],
        [InlineKeyboardButton(text="⬅️ Отмена", callback_data=f"cancel_upload_{language_id}")]
    ])
    return keyboard


def get_word_actions_keyboard(word_id: str, language_id: str) -> InlineKeyboardMarkup:
    """
    Создает клавиатуру с действиями для слова.
    
    Args:
        word_id (str): ID слова
        language_id (str): ID языка
        
    Returns:
        InlineKeyboardMarkup: Клавиатура с кнопками действий для слова
    """
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✏️ Редактировать", callback_data=f"edit_word_{word_id}")],
        [InlineKeyboardButton(text="🔍 Найти другое слово", callback_data=f"search_word_by_number_{language_id}")],
        [InlineKeyboardButton(text="⬅️ Назад к языку", callback_data=f"edit_language_{language_id}")]
    ])
    return keyboard