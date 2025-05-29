"""
Constants for callback_data used throughout the bot.
This helps avoid typos and makes callback management easier.
UPDATED: Added individual hint settings callbacks.
"""

import re
from typing import Dict, Optional, Tuple


class CallbackData:
    """Constants for callback data patterns."""
    
    # User word actions
    WORD_KNOW = "word_know"
    WORD_DONT_KNOW = "word_dont_know"
    SHOW_WORD = "show_word"
    NEXT_WORD = "next_word"
    CONFIRM_NEXT_WORD = "confirm_next_word"
    TOGGLE_WORD_SKIP = "toggle_word_skip"
    
    # Hint actions (templates)
    HINT_CREATE_TEMPLATE = "hint_create_{hint_type}_{word_id}"
    HINT_EDIT_TEMPLATE = "hint_edit_{hint_type}_{word_id}"
    HINT_TOGGLE_TEMPLATE = "hint_toggle_{hint_type}_{word_id}"
    HINT_VIEW_TEMPLATE = "hint_view_{hint_type}_{word_id}"
    
    # Settings actions
    SETTINGS_START_WORD = "settings_start_word"
    SETTINGS_TOGGLE_SKIP_MARKED = "settings_toggle_skip_marked"
    SETTINGS_TOGGLE_CHECK_DATE = "settings_toggle_check_date"
    SETTINGS_TOGGLE_SHOW_DEBUG = "settings_toggle_show_debug"
    
    # УДАЛЕНО: SETTINGS_TOGGLE_SHOW_HINTS - заменено на индивидуальные настройки
    
    # НОВОЕ: Индивидуальные настройки подсказок
    SETTINGS_TOGGLE_HINT_MEANING = "settings_toggle_hint_meaning"
    SETTINGS_TOGGLE_HINT_PHONETICASSOCIATION = "settings_toggle_hint_phoneticassociation"
    SETTINGS_TOGGLE_HINT_PHONETICSOUND = "settings_toggle_hint_phoneticsound"
    SETTINGS_TOGGLE_HINT_WRITING = "settings_toggle_hint_writing"
    
    # Language selection
    LANG_SELECT_TEMPLATE = "lang_select_{language_id}"
    
    # Admin actions
    ADMIN_LANGUAGES = "admin_languages"
    ADMIN_USERS = "admin_users"
    ADMIN_STATS = "admin_stats"
    ADMIN_STATS_CALLBACK = "admin_stats_callback"
    
    # Admin language management
    CREATE_LANGUAGE = "create_language"
    VIEW_LANGUAGES = "view_languages"
    EDIT_LANGUAGE_TEMPLATE = "edit_language_{language_id}"
    DELETE_LANGUAGE_TEMPLATE = "delete_language_{language_id}"

    CONFIRM_DELETE_TEMPLATE = "confirm_{action}_{entity_id}"
    CANCEL_DELETE_TEMPLATE = "cancel_{action}_{entity_id}"
    
    # Admin file upload
    UPLOAD_TO_LANG_TEMPLATE = "upload_to_lang_{language_id}"
    COLUMN_TEMPLATE = "column_template_{template_id}_{language_id}"
    CUSTOM_COLUMNS_TEMPLATE = "custom_columns_{language_id}"
    CANCEL_UPLOAD_TEMPLATE = "cancel_upload_{language_id}"
    
    # File upload actions
    CONFIRM_UPLOAD = "confirm_upload"
    CANCEL_UPLOAD = "cancel_upload"

    # File upload settings
    TOGGLE_HEADERS = "toggle_headers"
    TOGGLE_CLEAR_EXISTING = "toggle_clear_existing"
    CONFIRM_UPLOAD = "confirm_upload"
    BACK_TO_SETTINGS = "back_to_settings"    

    # Column configuration
    SELECT_COLUMN_TYPE = "select_column_type"    
        
    # Navigation
    BACK_TO_START = "back_to_start"
    BACK_TO_ADMIN = "back_to_admin"
    BACK_TO_LANGUAGES = "back_to_languages"
    BACK_TO_WORD = "back_to_word"
    
    # Additional actions
    CANCEL_ACTION = "cancel_action"
    PREVIOUS_WORD = "previous_word"
    
    # Pagination
    USERS_PAGE_TEMPLATE = "users_page_{page_number}"
    PAGE_INFO = "page_info"


# НОВОЕ: Словарь для маппинга callback'ов индивидуальных настроек подсказок
HINT_SETTINGS_CALLBACKS = {
    "show_hint_meaning": CallbackData.SETTINGS_TOGGLE_HINT_MEANING,
    "show_hint_phoneticassociation": CallbackData.SETTINGS_TOGGLE_HINT_PHONETICASSOCIATION,
    "show_hint_phoneticsound": CallbackData.SETTINGS_TOGGLE_HINT_PHONETICSOUND,
    "show_hint_writing": CallbackData.SETTINGS_TOGGLE_HINT_WRITING,
}

# НОВОЕ: Обратный маппинг для парсинга callback'ов
HINT_SETTINGS_CALLBACKS_REVERSE = {v: k for k, v in HINT_SETTINGS_CALLBACKS.items()}


class CallbackParser:
    """Helper class for parsing callback data."""
    
    # Regex patterns for parsing callbacks
    PATTERNS = {
        'hint_action': re.compile(r"hint_(create|edit|toggle|view)_(\w+)_(.+)"),
        'lang_select': re.compile(r"lang_select_(.+)"),
        'edit_language': re.compile(r"edit_language_(.+)"),
        'delete_language': re.compile(r"delete_language_(.+)"),
        'confirm_action': re.compile(r"confirm_(\w+)_(.+)"),
        'cancel_action': re.compile(r"cancel_(\w+)_(.+)"),
        'upload_to_lang': re.compile(r"upload_to_lang_(.+)"),
        'column_template': re.compile(r"column_template_(\d+)_(.+)"),
        'users_page': re.compile(r"users_page_(\d+)"),
        # НОВОЕ: Паттерн для индивидуальных настроек подсказок
        'hint_setting_toggle': re.compile(r"settings_toggle_hint_(\w+)"),
    }
    
    @classmethod
    def parse_hint_action(cls, callback_data: str) -> Optional[Tuple[str, str, str]]:
        """
        Parse hint action callback data.
        
        Args:
            callback_data: The callback data string
            
        Returns:
            Tuple of (action, hint_type, word_id) or None if no match
        """
        match = cls.PATTERNS['hint_action'].match(callback_data)
        if match:
            return match.groups()
        return None
    
    @classmethod
    def parse_language_selection(cls, callback_data: str) -> Optional[str]:
        """
        Parse language selection callback data.
        
        Args:
            callback_data: The callback data string
            
        Returns:
            Language ID or None if no match
        """
        match = cls.PATTERNS['lang_select'].match(callback_data)
        if match:
            return match.group(1)
        return None
    
    @classmethod
    def parse_edit_language(cls, callback_data: str) -> Optional[str]:
        """
        Parse edit language callback data.
        
        Args:
            callback_data: The callback data string
            
        Returns:
            Language ID or None if no match
        """
        match = cls.PATTERNS['edit_language'].match(callback_data)
        if match:
            return match.group(1)
        return None
    
    @classmethod
    def parse_confirm_action(cls, callback_data: str) -> Optional[Tuple[str, str]]:
        """
        Parse confirmation action callback data.
        
        Args:
            callback_data: The callback data string
            
        Returns:
            Tuple of (action, entity_id) or None if no match
        """
        match = cls.PATTERNS['confirm_action'].match(callback_data)
        if match:
            return match.groups()
        return None
    
    @classmethod
    def parse_users_page(cls, callback_data: str) -> Optional[int]:
        """
        Parse users page callback data.
        
        Args:
            callback_data: The callback data string
            
        Returns:
            Page number or None if no match
        """
        match = cls.PATTERNS['users_page'].match(callback_data)
        if match:
            return int(match.group(1))
        return None
    
    # НОВОЕ: Парсер для индивидуальных настроек подсказок
    @classmethod
    def parse_hint_setting_toggle(cls, callback_data: str) -> Optional[str]:
        """
        Parse hint setting toggle callback data.
        
        Args:
            callback_data: The callback data string
            
        Returns:
            Hint type or None if no match
        """
        match = cls.PATTERNS['hint_setting_toggle'].match(callback_data)
        if match:
            return match.group(1)
        return None


def format_hint_callback(action: str, hint_type: str, word_id: str) -> str:
    """
    Format hint callback data.
    
    Args:
        action: The action (create, edit, toggle, view)
        hint_type: The hint type
        word_id: The word ID
        
    Returns:
        Formatted callback data string
    """
    return f"hint_{action}_{hint_type}_{word_id}"


def format_language_callback(language_id: str) -> str:
    """
    Format language selection callback data.
    
    Args:
        language_id: The language ID
        
    Returns:
        Formatted callback data string
    """
    return f"lang_select_{language_id}"


def format_admin_callback(action: str, entity_id: str = None) -> str:
    """
    Format admin action callback data.
    
    Args:
        action: The admin action
        entity_id: Optional entity ID
        
    Returns:
        Formatted callback data string
    """
    if entity_id:
        return f"{action}_{entity_id}"
    return action


# НОВОЕ: Функции для работы с индивидуальными настройками подсказок
def get_hint_setting_callback(setting_key: str) -> Optional[str]:
    """
    Get callback data for a hint setting.
    
    Args:
        setting_key: The hint setting key (e.g., 'show_hint_meaning')
        
    Returns:
        Callback data string or None if not found
    """
    return HINT_SETTINGS_CALLBACKS.get(setting_key)


def get_hint_setting_from_callback(callback_data: str) -> Optional[str]:
    """
    Get hint setting key from callback data.
    
    Args:
        callback_data: The callback data string
        
    Returns:
        Setting key string or None if not found
    """
    return HINT_SETTINGS_CALLBACKS_REVERSE.get(callback_data)


def is_hint_setting_callback(callback_data: str) -> bool:
    """
    Check if callback data is for a hint setting toggle.
    
    Args:
        callback_data: The callback data string
        
    Returns:
        True if it's a hint setting callback, False otherwise
    """
    return callback_data in HINT_SETTINGS_CALLBACKS_REVERSE


# НОВОЕ: Функция для генерации всех callback'ов настроек подсказок
def get_all_hint_setting_callbacks() -> Dict[str, str]:
    """
    Get all hint setting callbacks.
    
    Returns:
        Dictionary mapping setting keys to callback data
    """
    return HINT_SETTINGS_CALLBACKS.copy()


def format_hint_setting_callback(hint_type: str) -> str:
    """
    Format callback data for hint setting toggle.
    
    Args:
        hint_type: The hint type (meaning, phoneticassociation, etc.)
        
    Returns:
        Formatted callback data string
    """
    return f"settings_toggle_hint_{hint_type}"
