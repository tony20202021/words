"""
Refactored keyboards for admin interface.
Now uses centralized callback constants and improved callback generation.
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


def get_back_to_languages_keyboard() -> InlineKeyboardMarkup:
    """
    Create keyboard with back to languages button.
    
    Returns:
        InlineKeyboardMarkup: Back to languages keyboard
    """
    builder = InlineKeyboardBuilder()
    
    builder.add(InlineKeyboardButton(
        text="⬅️ Назад к списку языков", 
        callback_data=CallbackData.BACK_TO_LANGUAGES
    ))
    
    return builder.as_markup()


def get_back_to_admin_keyboard() -> InlineKeyboardMarkup:
    """
    Create keyboard with back to admin button.
    
    Returns:
        InlineKeyboardMarkup: Back to admin keyboard
    """
    builder = InlineKeyboardBuilder()
    
    builder.add(InlineKeyboardButton(
        text="⬅️ Назад к меню администратора", 
        callback_data=CallbackData.BACK_TO_ADMIN
    ))
    
    return builder.as_markup()


def get_yes_no_keyboard(action: str, entity_id: str) -> InlineKeyboardMarkup:
    """
    Create keyboard with Yes/No buttons for confirmation.
    Now uses centralized callback constants.
    
    Args:
        action: Action type (e.g., "delete_language")
        entity_id: ID of the entity
        
    Returns:
        InlineKeyboardMarkup: Yes/No confirmation keyboard
    """
    builder = InlineKeyboardBuilder()
    
    builder.add(InlineKeyboardButton(
        text="✅ Да", 
        callback_data=CallbackData.CONFIRM_DELETE_TEMPLATE.format(action=action, entity_id=entity_id)
    ))
    
    builder.add(InlineKeyboardButton(
        text="❌ Нет", 
        callback_data=CallbackData.CANCEL_DELETE_TEMPLATE.format(action=action, entity_id=entity_id)
    ))
    
    builder.adjust(2)  # Two buttons in one row
    return builder.as_markup()


def get_upload_columns_keyboard(language_id: str) -> InlineKeyboardMarkup:
    """
    Create keyboard for configuring upload columns.
    Now uses centralized callback constants.
    
    Args:
        language_id: ID of the language
        
    Returns:
        InlineKeyboardMarkup: Column configuration keyboard
    """
    builder = InlineKeyboardBuilder()
    
    # Predefined templates
    builder.add(InlineKeyboardButton(
        text="1️⃣ Номер, слово, транскрипция, перевод", 
        callback_data=CallbackData.COLUMN_TEMPLATE.format(template_id="1", language_id=language_id)
    ))
    
    builder.add(InlineKeyboardButton(
        text="2️⃣ Номер, перевод, слово, транскрипция", 
        callback_data=CallbackData.COLUMN_TEMPLATE.format(template_id="2", language_id=language_id)
    ))
    
    builder.add(InlineKeyboardButton(
        text="3️⃣ Слово, транскрипция, перевод, номер", 
        callback_data=CallbackData.COLUMN_TEMPLATE.format(template_id="3", language_id=language_id)
    ))
    
    builder.add(InlineKeyboardButton(
        text="4️⃣ Настроить порядок вручную", 
        callback_data=CallbackData.CUSTOM_COLUMNS_TEMPLATE.format(language_id=language_id)
    ))
    
    builder.add(InlineKeyboardButton(
        text="⬅️ Отмена", 
        callback_data=CallbackData.CANCEL_UPLOAD_TEMPLATE.format(language_id=language_id)
    ))
    
    builder.adjust(1)  # One button per row
    return builder.as_markup()


def get_word_actions_keyboard(word_id: str, language_id: str) -> InlineKeyboardMarkup:
    """
    Create keyboard with word action buttons.
    
    Args:
        word_id: ID of the word
        language_id: ID of the language
        
    Returns:
        InlineKeyboardMarkup: Word actions keyboard
    """
    builder = InlineKeyboardBuilder()
    
    builder.add(InlineKeyboardButton(
        text="✏️ Редактировать", 
        callback_data=f"edit_word_{word_id}"
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
        text="👑 Изменить права админа", 
        callback_data=f"toggle_admin_{user_id}"
    ))
    
    builder.add(InlineKeyboardButton(
        text="⬅️ Назад к списку", 
        callback_data=CallbackData.ADMIN_USERS
    ))
    
    builder.adjust(1)  # One button per row
    return builder.as_markup()


def create_file_upload_keyboard(language_id: str) -> InlineKeyboardMarkup:
    """
    Create keyboard for file upload options.
    
    Args:
        language_id: ID of the target language
        
    Returns:
        InlineKeyboardMarkup: File upload options keyboard
    """
    builder = InlineKeyboardBuilder()
    
    builder.add(InlineKeyboardButton(
        text="📁 Загрузить новый файл",
        callback_data=CallbackData.UPLOAD_TO_LANG_TEMPLATE.format(language_id=language_id)
    ))
    
    builder.add(InlineKeyboardButton(
        text="🔄 Заменить все слова",
        callback_data=f"replace_all_words_{language_id}"
    ))
    
    builder.add(InlineKeyboardButton(
        text="➕ Добавить к существующим",
        callback_data=f"append_words_{language_id}"
    ))
    
    builder.add(InlineKeyboardButton(
        text="⬅️ Отмена",
        callback_data=CallbackData.CANCEL_UPLOAD_TEMPLATE.format(language_id=language_id)
    ))
    
    builder.adjust(1)  # One button per row
    return builder.as_markup()


def create_language_management_keyboard() -> InlineKeyboardMarkup:
    """
    Create keyboard for language management main menu.
    
    Returns:
        InlineKeyboardMarkup: Language management keyboard
    """
    builder = InlineKeyboardBuilder()
    
    builder.add(InlineKeyboardButton(
        text="📋 Просмотреть языки",
        callback_data=CallbackData.VIEW_LANGUAGES
    ))
    
    builder.add(InlineKeyboardButton(
        text="➕ Создать новый язык",
        callback_data=CallbackData.CREATE_LANGUAGE
    ))
    
    builder.add(InlineKeyboardButton(
        text="📊 Статистика языков",
        callback_data="languages_stats"
    ))
    
    builder.add(InlineKeyboardButton(
        text="⬅️ Назад в админку",
        callback_data=CallbackData.BACK_TO_ADMIN
    ))
    
    builder.adjust(1)  # One button per row
    return builder.as_markup()


def create_confirmation_keyboard(
    action: str, 
    entity_id: str, 
    confirm_text: str = "✅ Подтвердить",
    cancel_text: str = "❌ Отменить"
) -> InlineKeyboardMarkup:
    """
    Create a generic confirmation keyboard.
    
    Args:
        action: Action to confirm
        entity_id: ID of the entity
        confirm_text: Text for confirm button
        cancel_text: Text for cancel button
        
    Returns:
        InlineKeyboardMarkup: Confirmation keyboard
    """
    builder = InlineKeyboardBuilder()
    
    builder.add(InlineKeyboardButton(
        text=confirm_text,
        callback_data=CallbackData.CONFIRM_DELETE_TEMPLATE.format(action=action, entity_id=entity_id)
    ))
    
    builder.add(InlineKeyboardButton(
        text=cancel_text,
        callback_data=CallbackData.CANCEL_DELETE_TEMPLATE.format(action=action, entity_id=entity_id)
    ))
    
    builder.adjust(2)  # Two buttons in one row
    return builder.as_markup()


def create_admin_stats_keyboard() -> InlineKeyboardMarkup:
    """
    Create keyboard for admin statistics menu.
    
    Returns:
        InlineKeyboardMarkup: Admin stats keyboard
    """
    builder = InlineKeyboardBuilder()
    
    builder.add(InlineKeyboardButton(
        text="👥 Статистика пользователей",
        callback_data="admin_users_stats"
    ))
    
    builder.add(InlineKeyboardButton(
        text="🌐 Статистика языков",
        callback_data="admin_languages_stats"
    ))
    
    builder.add(InlineKeyboardButton(
        text="📝 Статистика слов",
        callback_data="admin_words_stats"
    ))
    
    builder.add(InlineKeyboardButton(
        text="📈 Общая статистика",
        callback_data="admin_general_stats"
    ))
    
    builder.add(InlineKeyboardButton(
        text="⬅️ Назад в админку",
        callback_data=CallbackData.BACK_TO_ADMIN
    ))
    
    builder.adjust(2, 2, 1)  # 2-2-1 layout
    return builder.as_markup()


# Utility functions for creating specific button types
def create_back_button(callback_data: str, text: str = "⬅️ Назад") -> InlineKeyboardButton:
    """Create a back button with custom callback data."""
    return InlineKeyboardButton(text=text, callback_data=callback_data)


def create_admin_action_button(text: str, action: str, entity_id: str = None) -> InlineKeyboardButton:
    """Create an admin action button with proper callback data."""
    callback_data = format_admin_callback(action, entity_id)
    return InlineKeyboardButton(text=text, callback_data=callback_data)


def create_language_button(language: dict) -> InlineKeyboardButton:
    """Create a button for language selection."""
    lang_id = language.get('_id', language.get('id'))
    display_text = f"{language['name_ru']} ({language['name_foreign']})"
    callback_data = CallbackData.EDIT_LANGUAGE_TEMPLATE.format(language_id=lang_id)
    
    return InlineKeyboardButton(text=display_text, callback_data=callback_data)


def create_user_button(user: dict) -> InlineKeyboardButton:
    """Create a button for user selection."""
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
    
    return InlineKeyboardButton(
        text=display_name,
        callback_data=f"view_user_{user_id}"
    )
