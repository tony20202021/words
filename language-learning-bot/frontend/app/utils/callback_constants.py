"""
Constants for callback_data used throughout the bot.
This helps avoid typos and makes callback management easier.
UPDATED: Added word image display callbacks.
UPDATED: Added word editing and deletion callbacks.
UPDATED: Added admin edit from study callbacks.
UPDATED: Added writing image callbacks for hieroglyphic languages.
UPDATED: Added messaging callbacks for admin message broadcasting.
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
    
    # Word image actions
    SHOW_BIG = "show_big"
    BACK_FROM_BIG = "back_from_big"
    
    # НОВОЕ: Writing image actions (картинки написания)
    SHOW_WRITING_IMAGE = "show_writing_image"
    BACK_FROM_WRITING_IMAGE = "back_from_writing_image"
    
    # Admin edit from study
    ADMIN_EDIT_WORD_FROM_STUDY = "admin_edit_word_from_study"
    ADMIN_EDIT_WORD_FROM_STUDY_TEMPLATE = "admin_edit_word_from_study_{word_id}"
    BACK_TO_STUDY_FROM_ADMIN = "back_to_study_from_admin"
    
    # Hint actions (templates)
    HINT_CREATE_TEMPLATE = "hint_create_{hint_type}_{word_id}"
    HINT_EDIT_TEMPLATE = "hint_edit_{hint_type}_{word_id}"
    HINT_TOGGLE_TEMPLATE = "hint_toggle_{hint_type}_{word_id}"
    HINT_VIEW_TEMPLATE = "hint_view_{hint_type}_{word_id}"
    
    # Settings actions
    SETTINGS_START_WORD = "settings_start_word"
    SETTINGS_TOGGLE_SKIP_MARKED = "settings_toggle_skip_marked"
    SETTINGS_TOGGLE_CHECK_DATE = "settings_toggle_check_date"
    SETTINGS_TOGGLE_SHOW_CHECK_DATE = "settings_toggle_show_check_date"
    SETTINGS_TOGGLE_SHOW_BIG = "settings_toggle_show_big"
    SETTINGS_TOGGLE_SHOW_SHORT_CAPTIONS = "settings_toggle_show_short_captions"
    SETTINGS_TOGGLE_SHOW_DEBUG = "settings_toggle_show_debug"
    
    # Индивидуальные настройки подсказок
    SETTINGS_TOGGLE_HINT_MEANING = "settings_toggle_hint_meaning"
    SETTINGS_TOGGLE_HINT_PHONETICASSOCIATION = "settings_toggle_hint_phoneticassociation"
    SETTINGS_TOGGLE_HINT_PHONETICSOUND = "settings_toggle_hint_phoneticsound"
    SETTINGS_TOGGLE_HINT_WRITING = "settings_toggle_hint_writing"
    
    SETTINGS_TOGGLE_RECEIVE_MESSAGES = "settings_toggle_receive_messages"
    
    # НОВОЕ: Настройка картинок написания
    SETTINGS_TOGGLE_WRITING_IMAGES = "settings_toggle_writing_images"
    
    # Language selection
    LANG_SELECT_TEMPLATE = "lang_select_{language_id}"
    
    # Admin actions
    ADMIN_LANGUAGES = "admin_languages"
    ADMIN_USERS = "admin_users"
    ADMIN_STATS = "admin_stats"
    ADMIN_STATS_CALLBACK = "admin_stats_callback"
    ADMIN_SEND_MESSAGE_TO_ALL = "admin_send_message_to_all"
    
    # НОВОЕ: Messaging callbacks
    CONFIRM_MESSAGING = "confirm_messaging"
    CANCEL_MESSAGING = "cancel_messaging"
    
    # Admin language management
    CREATE_LANGUAGE = "create_language"
    VIEW_LANGUAGES = "view_languages"
    EDIT_LANGUAGE_TEMPLATE = "edit_language_{language_id}"
    DELETE_LANGUAGE_TEMPLATE = "delete_language_{language_id}"

    # Admin word management
    EDIT_WORD_TEMPLATE = "edit_word_{word_id}"
    DELETE_WORD_TEMPLATE = "delete_word_{word_id}"
    EDIT_WORDFIELD_FOREIGN_TEMPLATE = "edit_wordfield_foreign_{word_id}"
    EDIT_WORDFIELD_TRANSLATION_TEMPLATE = "edit_wordfield_translation_{word_id}"
    EDIT_WORDFIELD_TRANSCRIPTION_TEMPLATE = "edit_wordfield_transcription_{word_id}"
    EDIT_WORDFIELD_NUMBER_TEMPLATE = "edit_wordfield_number_{word_id}"
    CONFIRM_WORD_DELETE_TEMPLATE = "confirm_word_delete_{word_id}"
    CANCEL_WORD_DELETE_TEMPLATE = "cancel_word_delete_{word_id}"

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
    BACK_TO_WORD_DETAILS = "back_to_word_details"
    
    # Additional actions
    CANCEL_ACTION = "cancel_action"
    PREVIOUS_WORD = "previous_word"
    
    # Pagination
    USERS_PAGE_TEMPLATE = "users_page_{page_number}"
    PAGE_INFO = "page_info"


# Словарь для маппинга callback'ов индивидуальных настроек подсказок
HINT_SETTINGS_CALLBACKS = {
    "show_hint_meaning": CallbackData.SETTINGS_TOGGLE_HINT_MEANING,
    "show_hint_phoneticassociation": CallbackData.SETTINGS_TOGGLE_HINT_PHONETICASSOCIATION,
    "show_hint_phoneticsound": CallbackData.SETTINGS_TOGGLE_HINT_PHONETICSOUND,
    "show_hint_writing": CallbackData.SETTINGS_TOGGLE_HINT_WRITING,
}

# НОВОЕ: Словарь для маппинга настройки картинок написания
WRITING_IMAGE_SETTINGS_CALLBACKS = {
    "show_writing_images": CallbackData.SETTINGS_TOGGLE_WRITING_IMAGES,
}

# Обратный маппинг для парсинга callback'ов
HINT_SETTINGS_CALLBACKS_REVERSE = {v: k for k, v in HINT_SETTINGS_CALLBACKS.items()}

# НОВОЕ: Обратный маппинг для настроек картинок написания
WRITING_IMAGE_SETTINGS_CALLBACKS_REVERSE = {v: k for k, v in WRITING_IMAGE_SETTINGS_CALLBACKS.items()}

# НОВОЕ: Объединенный маппинг всех настроек
ALL_SETTINGS_CALLBACKS = {
    **HINT_SETTINGS_CALLBACKS,
    **WRITING_IMAGE_SETTINGS_CALLBACKS
}

ALL_SETTINGS_CALLBACKS_REVERSE = {
    **HINT_SETTINGS_CALLBACKS_REVERSE,
    **WRITING_IMAGE_SETTINGS_CALLBACKS_REVERSE
}


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
        'hint_setting_toggle': re.compile(r"settings_toggle_hint_(\w+)"),
        'edit_word': re.compile(r"edit_word_(.+)"),
        'delete_word': re.compile(r"delete_word_(.+)"),
        'edit_wordfield': re.compile(r"edit_wordfield_(foreign|translation|transcription|number)_(.+)"),
        'confirm_word_delete': re.compile(r"confirm_word_delete_(.+)"),
        'cancel_word_delete': re.compile(r"cancel_word_delete_(.+)"),
        'admin_edit_from_study': re.compile(r"admin_edit_word_from_study_(.+)"),
        # НОВОЕ: Парсеры для настроек картинок написания
        'writing_images_setting_toggle': re.compile(r"settings_toggle_writing_images"),
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

    @classmethod
    def parse_edit_word(cls, callback_data: str) -> Optional[str]:
        """
        Parse edit word callback data.
        
        Args:
            callback_data: The callback data string
            
        Returns:
            Word ID or None if no match
        """
        match = cls.PATTERNS['edit_word'].match(callback_data)
        if match:
            return match.group(1)
        return None
    
    @classmethod
    def parse_delete_word(cls, callback_data: str) -> Optional[str]:
        """
        Parse delete word callback data.
        
        Args:
            callback_data: The callback data string
            
        Returns:
            Word ID or None if no match
        """
        match = cls.PATTERNS['delete_word'].match(callback_data)
        if match:
            return match.group(1)
        return None
    
    @classmethod
    def parse_edit_wordfield(cls, callback_data: str) -> Optional[Tuple[str, str]]:
        """
        Parse edit word field callback data.
        
        Args:
            callback_data: The callback data string
            
        Returns:
            Tuple of (field_name, word_id) or None if no match
        """
        match = cls.PATTERNS['edit_wordfield'].match(callback_data)
        if match:
            return match.groups()
        return None
    
    @classmethod
    def parse_confirm_word_delete(cls, callback_data: str) -> Optional[str]:
        """
        Parse confirm word delete callback data.
        
        Args:
            callback_data: The callback data string
            
        Returns:
            Word ID or None if no match
        """
        match = cls.PATTERNS['confirm_word_delete'].match(callback_data)
        if match:
            return match.group(1)
        return None
    
    @classmethod
    def parse_cancel_word_delete(cls, callback_data: str) -> Optional[str]:
        """
        Parse cancel word delete callback data.
        
        Args:
            callback_data: The callback data string
            
        Returns:
            Word ID or None if no match
        """
        match = cls.PATTERNS['cancel_word_delete'].match(callback_data)
        if match:
            return match.group(1)
        return None

    @classmethod
    def parse_admin_edit_from_study(cls, callback_data: str) -> Optional[str]:
        """
        Parse admin edit from study callback data.
        
        Args:
            callback_data: The callback data string
            
        Returns:
            Word ID or None if no match
        """
        match = cls.PATTERNS['admin_edit_from_study'].match(callback_data)
        if match:
            return match.group(1)
        return None

    # НОВОЕ: Парсер для настроек картинок написания
    @classmethod
    def is_writing_images_setting_toggle(cls, callback_data: str) -> bool:
        """
        Check if callback data is for writing images setting toggle.
        
        Args:
            callback_data: The callback data string
            
        Returns:
            True if it's a writing images setting callback, False otherwise
        """
        match = cls.PATTERNS['writing_images_setting_toggle'].match(callback_data)
        return match is not None


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


def format_admin_edit_from_study_callback(word_id: str) -> str:
    """
    Format admin edit from study callback data.
    
    Args:
        word_id: The word ID
        
    Returns:
        Formatted callback data string
    """
    return CallbackData.ADMIN_EDIT_WORD_FROM_STUDY_TEMPLATE.format(word_id=word_id)


def get_hint_setting_callback(setting_key: str) -> Optional[str]:
    """
    Get callback data for a hint setting.
    
    Args:
        setting_key: The hint setting key (e.g., 'show_hint_meaning')
        
    Returns:
        Callback data string or None if not found
    """
    return ALL_SETTINGS_CALLBACKS.get(setting_key)


def get_hint_setting_from_callback(callback_data: str) -> Optional[str]:
    """
    Get hint setting key from callback data.
    
    Args:
        callback_data: The callback data string
        
    Returns:
        Setting key string or None if not found
    """
    return ALL_SETTINGS_CALLBACKS_REVERSE.get(callback_data)


def is_hint_setting_callback(callback_data: str) -> bool:
    """
    Check if callback data is for a hint setting toggle.
    
    Args:
        callback_data: The callback data string
        
    Returns:
        True if it's a hint setting callback, False otherwise
    """
    return callback_data in HINT_SETTINGS_CALLBACKS_REVERSE


# НОВОЕ: Функции для работы с настройками картинок написания
def is_writing_images_setting_callback(callback_data: str) -> bool:
    """
    Check if callback data is for writing images setting toggle.
    
    Args:
        callback_data: The callback data string
        
    Returns:
        True if it's a writing images setting callback, False otherwise
    """
    return callback_data in WRITING_IMAGE_SETTINGS_CALLBACKS_REVERSE


def is_any_setting_callback(callback_data: str) -> bool:
    """
    Check if callback data is for any setting toggle (hints or writing images).
    
    Args:
        callback_data: The callback data string
        
    Returns:
        True if it's any setting callback, False otherwise
    """
    return callback_data in ALL_SETTINGS_CALLBACKS_REVERSE


def get_setting_from_callback(callback_data: str) -> Optional[str]:
    """
    Get setting key from any callback data (hints or writing images).
    
    Args:
        callback_data: The callback data string
        
    Returns:
        Setting key string or None if not found
    """
    return ALL_SETTINGS_CALLBACKS_REVERSE.get(callback_data)
    