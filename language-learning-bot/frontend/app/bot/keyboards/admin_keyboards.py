"""
Refactored keyboards for admin interface.
Now uses centralized callback constants and improved callback generation.
UPDATED: Added word editing and deletion keyboards.
UPDATED: Added export words button.
"""

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

# Import callback constants and utilities
from app.utils.callback_constants import CallbackData, format_admin_callback

def get_admin_keyboard() -> InlineKeyboardMarkup:
    """
    Create keyboard for admin menu.
    Now uses centralized callback constants.
    
    Returns:
        InlineKeyboardMarkup: Admin menu keyboard
    """
    builder = InlineKeyboardBuilder()
    
    builder.add(InlineKeyboardButton(
        text="👨‍💼 Управление языками", 
        callback_data=CallbackData.ADMIN_LANGUAGES
    ))
    
    builder.add(InlineKeyboardButton(
        text="👥 Управление пользователями", 
        callback_data=CallbackData.ADMIN_USERS
    ))
    
    builder.add(InlineKeyboardButton(
        text="📊 Статистика", 
        callback_data=CallbackData.ADMIN_STATS_CALLBACK
    ))
    
    builder.add(InlineKeyboardButton(
        text="📤 Сообщение всем пользователям", 
        callback_data=CallbackData.ADMIN_SEND_MESSAGE_TO_ALL
    ))

    builder.add(InlineKeyboardButton(
        text="⬅️ Выйти из режима администратора", 
        callback_data=CallbackData.BACK_TO_START
    ))
    
    builder.adjust(1)  # One button per row
    return builder.as_markup()


def get_languages_keyboard(languages: list) -> InlineKeyboardMarkup:
    """
    Create keyboard for languages list.
    Now uses centralized callback constants.
    
    Args:
        languages: List of language dictionaries
        
    Returns:
        InlineKeyboardMarkup: Languages keyboard
    """
    builder = InlineKeyboardBuilder()
    
    # Add language buttons
    for language in languages:
        lang_id = language.get('_id', language.get('id'))
        
        builder.add(InlineKeyboardButton(
            text=f"{language['name_ru']} ({language['name_foreign']})", 
            callback_data=CallbackData.EDIT_LANGUAGE_TEMPLATE.format(language_id=lang_id)
        ))
    
    # Add create new language button
    builder.add(InlineKeyboardButton(
        text="➕ Создать новый язык", 
        callback_data=CallbackData.CREATE_LANGUAGE
    ))
    
    # Add back button
    builder.add(InlineKeyboardButton(
        text="⬅️ Вернуться к администрированию", 
        callback_data=CallbackData.BACK_TO_ADMIN
    ))
    
    # Layout: one button per row for languages, then action buttons
    button_layout = [1] * len(languages) + [1, 1]  # Each language + create + back
    builder.adjust(*button_layout)
    
    return builder.as_markup()


def get_edit_language_keyboard(language_id: str) -> InlineKeyboardMarkup:
    """
    Create keyboard for editing a language.
    Now uses centralized callback constants.
    UPDATED: Added export words button.
    
    Args:
        language_id: ID of the language to edit
        
    Returns:
        InlineKeyboardMarkup: Language editing keyboard
    """
    builder = InlineKeyboardBuilder()
    
    builder.add(InlineKeyboardButton(
        text="✏️ Изменить русское название", 
        callback_data=f"edit_name_ru_{language_id}"
    ))
    
    builder.add(InlineKeyboardButton(
        text="✏️ Изменить оригинальное название", 
        callback_data=f"edit_name_foreign_{language_id}"
    ))
    
    builder.add(InlineKeyboardButton(
        text="📤 Загрузить файл со словами", 
        callback_data=CallbackData.UPLOAD_TO_LANG_TEMPLATE.format(language_id=language_id)
    ))
    
    builder.add(InlineKeyboardButton(
        text="📥 Экспорт слов", 
        callback_data=f"export_words_{language_id}"
    ))
    
    builder.add(InlineKeyboardButton(
        text="🔍 Найти слово по номеру", 
        callback_data=f"search_word_by_number_{language_id}"
    ))
    
    builder.add(InlineKeyboardButton(
        text="🗑️ Удалить язык", 
        callback_data=CallbackData.DELETE_LANGUAGE_TEMPLATE.format(language_id=language_id)
    ))
    
    builder.add(InlineKeyboardButton(
        text="⬅️ Назад к языкам", 
        callback_data=CallbackData.BACK_TO_LANGUAGES
    ))
    
    builder.adjust(1)  # One button per row
    return builder.as_markup()


def get_export_format_keyboard(language_id: str) -> InlineKeyboardMarkup:
    """
    Create keyboard for selecting export format.
    
    Args:
        language_id: ID of the language to export
        
    Returns:
        InlineKeyboardMarkup: Export format selection keyboard
    """
    builder = InlineKeyboardBuilder()
    
    builder.add(InlineKeyboardButton(
        text="📊 Excel (.xlsx)", 
        callback_data=f"export_format_{language_id}_xlsx"
    ))
    
    builder.add(InlineKeyboardButton(
        text="📄 CSV (.csv)", 
        callback_data=f"export_format_{language_id}_csv"
    ))
    
    builder.add(InlineKeyboardButton(
        text="🔧 JSON (.json)", 
        callback_data=f"export_format_{language_id}_json"
    ))
    
    builder.add(InlineKeyboardButton(
        text="⬅️ Назад к языку", 
        callback_data=CallbackData.EDIT_LANGUAGE_TEMPLATE.format(language_id=language_id)
    ))
    
    builder.adjust(1)  # One button per row
    return builder.as_markup()


def get_export_range_keyboard(language_id: str, format: str) -> InlineKeyboardMarkup:
    """
    Create keyboard for selecting export range.
    
    Args:
        language_id: ID of the language to export
        format: Export format (xlsx, csv, json)
        
    Returns:
        InlineKeyboardMarkup: Export range selection keyboard
    """
    builder = InlineKeyboardBuilder()
    
    builder.add(InlineKeyboardButton(
        text="📋 Все слова", 
        callback_data=f"export_range_{language_id}_{format}_all"
    ))
    
    builder.add(InlineKeyboardButton(
        text="🔢 Указать диапазон", 
        callback_data=f"export_range_{language_id}_{format}_range"
    ))
    
    builder.add(InlineKeyboardButton(
        text="⬅️ Назад к формату", 
        callback_data=f"export_words_{language_id}"
    ))
    
    builder.adjust(1)  # One button per row
    return builder.as_markup()


def get_word_actions_keyboard(word_id: str, language_id: str) -> InlineKeyboardMarkup:
    """
    Create keyboard with word action buttons.
    UPDATED: Enhanced with new edit and delete options.
    
    Args:
        word_id: ID of the word
        language_id: ID of the language
        
    Returns:
        InlineKeyboardMarkup: Word actions keyboard
    """
    builder = InlineKeyboardBuilder()
    
    builder.add(InlineKeyboardButton(
        text="✏️ Редактировать слово", 
        callback_data=CallbackData.EDIT_WORD_TEMPLATE.format(word_id=word_id)
    ))
    
    builder.add(InlineKeyboardButton(
        text="🗑️ Удалить слово", 
        callback_data=CallbackData.DELETE_WORD_TEMPLATE.format(word_id=word_id)
    ))
    
    builder.add(InlineKeyboardButton(
        text="🔍 Найти другое слово", 
        callback_data=f"search_word_by_number_{language_id}"
    ))
    
    builder.add(InlineKeyboardButton(
        text="⬅️ Назад к языку", 
        callback_data=CallbackData.EDIT_LANGUAGE_TEMPLATE.format(language_id=language_id)
    ))
    
    builder.adjust(1)  # One button per row
    return builder.as_markup()

def get_word_filed_edit_keyboard(word_id: str, language_id: str) -> InlineKeyboardMarkup:
    """
    Create keyboard for word editing menu.
    
    Args:
        word_id: ID of the word
        language_id: ID of the language
        
    Returns:
        InlineKeyboardMarkup: Word editing keyboard
    """
    builder = InlineKeyboardBuilder()
    
    builder.add(InlineKeyboardButton(
        text="🔤 Изменить иностранное слово", 
        callback_data=CallbackData.EDIT_WORDFIELD_FOREIGN_TEMPLATE.format(word_id=word_id)
    ))
    
    builder.add(InlineKeyboardButton(
        text="🇷🇺 Изменить перевод", 
        callback_data=CallbackData.EDIT_WORDFIELD_TRANSLATION_TEMPLATE.format(word_id=word_id)
    ))
    
    builder.add(InlineKeyboardButton(
        text="🔊 Изменить транскрипцию", 
        callback_data=CallbackData.EDIT_WORDFIELD_TRANSCRIPTION_TEMPLATE.format(word_id=word_id)
    ))
    
    builder.add(InlineKeyboardButton(
        text="🔊 Изменить радикалы", 
        callback_data=CallbackData.EDIT_WORDFIELD_RADICALS_TEMPLATE.format(word_id=word_id)
    ))
    
    builder.add(InlineKeyboardButton(
        text="🔊 Изменить ссылки", 
        callback_data=CallbackData.EDIT_WORDFIELD_REFERENCES_TEMPLATE.format(word_id=word_id)
    ))
    
    builder.add(InlineKeyboardButton(
        text="🔊 Изменить тоны", 
        callback_data=CallbackData.EDIT_WORDFIELD_TONES_TEMPLATE.format(word_id=word_id)
    ))
    
    builder.add(InlineKeyboardButton(
        text="🔢 Изменить номер слова", 
        callback_data=CallbackData.EDIT_WORDFIELD_NUMBER_TEMPLATE.format(word_id=word_id)
    ))
    
    builder.add(InlineKeyboardButton(
        text="⬅️ Назад к слову", 
        callback_data=CallbackData.BACK_TO_WORD_DETAILS
    ))
    
    builder.adjust(1)  # One button per row
    return builder.as_markup()


def get_word_delete_confirmation_keyboard(word_id: str) -> InlineKeyboardMarkup:
    """
    Create keyboard for word deletion confirmation.
    
    Args:
        word_id: ID of the word to delete
        
    Returns:
        InlineKeyboardMarkup: Word deletion confirmation keyboard
    """
    builder = InlineKeyboardBuilder()
    
    builder.add(InlineKeyboardButton(
        text="✅ Да, удалить слово", 
        callback_data=CallbackData.CONFIRM_WORD_DELETE_TEMPLATE.format(word_id=word_id)
    ))
    
    builder.add(InlineKeyboardButton(
        text="❌ Отменить удаление", 
        callback_data=CallbackData.CANCEL_WORD_DELETE_TEMPLATE.format(word_id=word_id)
    ))
    
    builder.adjust(2)  # Two buttons in one row
    return builder.as_markup()


def get_users_keyboard(users: list, page: int = 0, per_page: int = 10) -> InlineKeyboardMarkup:
    """
    Create keyboard for users list with pagination.
    Now uses centralized callback constants.
    
    Args:
        users: List of user dictionaries
        page: Current page number (starting from 0)
        per_page: Number of users per page
        
    Returns:
        InlineKeyboardMarkup: Users list keyboard with pagination
    """
    builder = InlineKeyboardBuilder()
    
    # Calculate page boundaries
    start_idx = page * per_page
    end_idx = min(start_idx + per_page, len(users))
    
    # Add user buttons for current page
    for i in range(start_idx, end_idx):
        user = users[i]
        user_id = user.get('_id', user.get('id'))
        username = user.get('username', 'Нет username')
        first_name = user.get('first_name', 'Без имени')
        
        # Format display name
        display_name = f"{first_name}"
        if username and username != 'Нет username':
            display_name += f" (@{username})"
        
        # Add admin indicator
        if user.get('is_admin', False):
            display_name += " 👑"
        
        builder.add(InlineKeyboardButton(
            text=display_name, 
            callback_data=f"view_user_{user_id}"
        ))
    
    # Add navigation buttons
    nav_buttons = []
    
    if page > 0:
        nav_buttons.append(InlineKeyboardButton(
            text="⬅️ Пред.", 
            callback_data=CallbackData.USERS_PAGE_TEMPLATE.format(page_number=page-1)
        ))
    
    if end_idx < len(users):
        nav_buttons.append(InlineKeyboardButton(
            text="След. ➡️", 
            callback_data=CallbackData.USERS_PAGE_TEMPLATE.format(page_number=page+1)
        ))
    
    if nav_buttons:
        builder.row(*nav_buttons)
    
    # Add page info
    total_pages = (len(users) + per_page - 1) // per_page
    if total_pages > 1:
        builder.add(InlineKeyboardButton(
            text=f"Стр. {page + 1}/{total_pages}",
            callback_data=CallbackData.PAGE_INFO
        ))
    
    # Add back button
    builder.add(InlineKeyboardButton(
        text="⬅️ Назад в админку", 
        callback_data=CallbackData.BACK_TO_ADMIN
    ))
    
    # Set layout: users, then navigation, then page info, then back
    users_count = end_idx - start_idx
    layout = [1] * users_count  # One button per user
    
    if nav_buttons:
        layout.append(len(nav_buttons))  # Navigation buttons row
    
    if total_pages > 1:
        layout.append(1)  # Page info button
    
    layout.append(1)  # Back button
    
    builder.adjust(*layout)
    return builder.as_markup()


def get_user_detail_keyboard(user_id: str) -> InlineKeyboardMarkup:
    """
    Create keyboard for user detail view.
    
    Args:
        user_id: ID of the user
        
    Returns:
        InlineKeyboardMarkup: User detail keyboard
    """
    builder = InlineKeyboardBuilder()
    
    builder.add(InlineKeyboardButton(
        text="📊 Подробная статистика", 
        callback_data=f"user_stats_{user_id}"
    ))
    
    builder.add(InlineKeyboardButton(
        text="⬅️ Назад к списку", 
        callback_data=CallbackData.ADMIN_USERS
    ))
    
    builder.adjust(1)  # One button per row
    return builder.as_markup()

def get_word_actions_keyboard_from_study(word_id: str, language_id: str) -> InlineKeyboardMarkup:
    """
    Create keyboard with word action buttons when coming from study mode.
    This keyboard includes a "Return to Study" button instead of regular admin navigation.
    
    Args:
        word_id: ID of the word
        language_id: ID of the language
        
    Returns:
        InlineKeyboardMarkup: Word actions keyboard for study context
    """
    builder = InlineKeyboardBuilder()
    
    builder.add(InlineKeyboardButton(
        text="✏️ Редактировать слово", 
        callback_data=CallbackData.EDIT_WORD_TEMPLATE.format(word_id=word_id)
    ))
    
    builder.add(InlineKeyboardButton(
        text="🗑️ Удалить слово", 
        callback_data=CallbackData.DELETE_WORD_TEMPLATE.format(word_id=word_id)
    ))
    
    # ОТЛИЧИЕ: Вместо обычной админ-навигации добавляем возврат к изучению
    builder.add(InlineKeyboardButton(
        text="⬅️ Вернуться к изучению", 
        callback_data=CallbackData.BACK_TO_STUDY_FROM_ADMIN
    ))
    
    builder.adjust(1)  # One button per row
    return builder.as_markup()


def get_word_edit_keyboard_from_study(word_id: str, language_id: str) -> InlineKeyboardMarkup:
    """
    Create keyboard for word editing menu when coming from study mode.
    
    Args:
        word_id: ID of the word
        language_id: ID of the language
        
    Returns:
        InlineKeyboardMarkup: Word editing keyboard for study context
    """
    builder = InlineKeyboardBuilder()
    
    builder.add(InlineKeyboardButton(
        text="🔤 Изменить иностранное слово", 
        callback_data=CallbackData.EDIT_WORDFIELD_FOREIGN_TEMPLATE.format(word_id=word_id)
    ))
    
    builder.add(InlineKeyboardButton(
        text="🇷🇺 Изменить перевод", 
        callback_data=CallbackData.EDIT_WORDFIELD_TRANSLATION_TEMPLATE.format(word_id=word_id)
    ))
    
    builder.add(InlineKeyboardButton(
        text="🔊 Изменить транскрипцию", 
        callback_data=CallbackData.EDIT_WORDFIELD_TRANSCRIPTION_TEMPLATE.format(word_id=word_id)
    ))
    
    builder.add(InlineKeyboardButton(
        text="🔢 Изменить номер слова", 
        callback_data=CallbackData.EDIT_WORDFIELD_NUMBER_TEMPLATE.format(word_id=word_id)
    ))
    
    # ОТЛИЧИЕ: Возврат к изучению вместо обычной админ-навигации  
    builder.add(InlineKeyboardButton(
        text="⬅️ Назад к слову", 
        callback_data=CallbackData.BACK_TO_WORD_DETAILS
    ))
    
    builder.add(InlineKeyboardButton(
        text="🏠 Вернуться к изучению", 
        callback_data=CallbackData.BACK_TO_STUDY_FROM_ADMIN
    ))
    
    builder.adjust(1)  # One button per row
    return builder.as_markup()


def get_word_delete_confirmation_keyboard_from_study(word_id: str) -> InlineKeyboardMarkup:
    """
    Create keyboard for word deletion confirmation when coming from study mode.
    
    Args:
        word_id: ID of the word to delete
        
    Returns:
        InlineKeyboardMarkup: Word deletion confirmation keyboard for study context
    """
    builder = InlineKeyboardBuilder()
    
    builder.add(InlineKeyboardButton(
        text="✅ Да, удалить слово", 
        callback_data=CallbackData.CONFIRM_WORD_DELETE_TEMPLATE.format(word_id=word_id)
    ))
    
    builder.add(InlineKeyboardButton(
        text="❌ Отменить удаление", 
        callback_data=CallbackData.CANCEL_WORD_DELETE_TEMPLATE.format(word_id=word_id)
    ))
    
    # ДОПОЛНИТЕЛЬНО: Быстрый возврат к изучению
    builder.add(InlineKeyboardButton(
        text="🏠 Вернуться к изучению", 
        callback_data=CallbackData.BACK_TO_STUDY_FROM_ADMIN
    ))
    
    builder.adjust(2, 1)  # Первая строка: 2 кнопки, вторая строка: 1 кнопка
    return builder.as_markup()
    
def get_upload_settings_keyboard(
    language_id: str,
    column_number: int,
    column_word: int,
    column_transcription: int,
    column_translation: int,
    column_radicals: int,
    column_references: int,
    column_tones: int
) -> InlineKeyboardMarkup:
    """
    Create keyboard for uploading settings.
    
    Returns:
        InlineKeyboardMarkup: Upload settings keyboard
    """
    # Создаем клавиатуру с настройками загрузки файла
    builder = InlineKeyboardBuilder()
    
    # Кнопки для настройки файла
    builder.add(InlineKeyboardButton(
        text='📝 Файл содержит заголовки: поменять на "Да"', 
        callback_data=CallbackData.TOGGLE_HEADERS
    ))
    builder.add(InlineKeyboardButton(
        text='🗑️ Очистить существующие слова: поменять на "Да"', 
        callback_data=CallbackData.TOGGLE_CLEAR_EXISTING
    ))
    
    # Добавляем информацию о текущих настройках колонок в кнопку
    column_info = f"(сейчас: {column_number}, {column_word}, {column_transcription}, {column_translation}, {column_radicals}, {column_references}, {column_tones})"
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
    
    # Настраиваем ширину строки клавиатуры (по 1 кнопке в ряд)
    builder.adjust(1)

    return builder.as_markup()
