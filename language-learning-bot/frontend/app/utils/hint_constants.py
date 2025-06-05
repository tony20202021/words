"""
Constants and mapping utilities for hint management.
UPDATED: Added individual hint settings constants.
UPDATED: Added writing images settings constants.
UPDATED: Removed hieroglyphic language restrictions - writing images are now controlled by user settings only.
"""

from typing import Dict, Tuple, List, Optional
import logging

# Configure logger
logger = logging.getLogger(__name__)

# Словарь соответствия типов подсказок их API ключам и отображаемым именам
HINT_TYPE_MAP: Dict[str, Tuple[str, str]] = {
    "meaning": ("hint_meaning", "Ассоциация на русском", "(рус)"),
    "phoneticassociation": ("hint_phoneticassociation", "Ассоциация для фонетики", "(фонетик)"),
    "phoneticsound": ("hint_phoneticsound", "Звучание по слогам", "(звук)"),
    "writing": ("hint_writing", "Ассоциация для написания", "(запись)")
}

# Иконки для разных типов подсказок - используем оригинальные
HINT_ICONS: Dict[str, str] = {
    "meaning": "🧠",
    "phoneticassociation": "💡",
    "phoneticsound": "🎵",
    "writing": "✍️"
}

# Порядок типов подсказок для отображения
HINT_ORDER: List[str] = [
    "meaning",
    "phoneticassociation",
    "phoneticsound",
    "writing"
]

DB_FIELD_HINT_KEY_MAPPING = {
    "hint_phoneticsound": "phoneticsound",
    "hint_phoneticassociation": "phoneticassociation",
    "hint_meaning": "meaning",
    "hint_writing": "writing"
}

# Маппинг типов подсказок к их настройкам
HINT_SETTINGS_MAP: Dict[str, str] = {
    "meaning": "show_hint_meaning",
    "phoneticassociation": "show_hint_phoneticassociation", 
    "phoneticsound": "show_hint_phoneticsound",
    "writing": "show_hint_writing"
}

# Краткие названия для настроек подсказок (для UI)
HINT_SETTINGS_NAMES: Dict[str, str] = {
    "show_hint_meaning": "Ассоциация на русском",
    "show_hint_phoneticassociation": "Ассоциация звучания",
    "show_hint_phoneticsound": "Звучание по слогам", 
    "show_hint_writing": "Ассоциация написания"
}

# Все ключи настроек подсказок
HINT_SETTING_KEYS = list(HINT_SETTINGS_MAP.values())

# Настройки для картинок написания
WRITING_IMAGE_SETTINGS_MAP: Dict[str, str] = {
    "writing_images": "show_writing_images"
}

# Названия для настроек картинок написания
WRITING_IMAGE_SETTINGS_NAMES: Dict[str, str] = {
    "show_writing_images": "Картинки написания"
}

# Все ключи настроек картинок написания
WRITING_IMAGE_SETTING_KEYS = list(WRITING_IMAGE_SETTINGS_MAP.values())

# Объединенные настройки (подсказки + картинки написания)
ALL_SETTINGS_MAP = {
    **HINT_SETTINGS_MAP,
    **WRITING_IMAGE_SETTINGS_MAP
}

ALL_SETTINGS_NAMES = {
    **HINT_SETTINGS_NAMES,
    **WRITING_IMAGE_SETTINGS_NAMES
}

ALL_SETTING_KEYS = HINT_SETTING_KEYS + WRITING_IMAGE_SETTING_KEYS

# Логирование констант при загрузке модуля для отладки
logger.info(f"Loaded hint types: {list(HINT_TYPE_MAP.keys())}")
logger.info(f"Loaded hint icons: {HINT_ICONS}")
logger.info(f"Loaded hint settings: {HINT_SETTING_KEYS}")
logger.info(f"Loaded writing image settings: {WRITING_IMAGE_SETTING_KEYS}")
logger.info(f"Loaded all settings: {ALL_SETTING_KEYS}")

def get_hint_key(hint_type: str) -> Optional[str]:
    """
    Get API key for a hint type.
    
    Args:
        hint_type: Hint type string
        
    Returns:
        str: API key for the hint type or None if not found
    """
    result = HINT_TYPE_MAP.get(hint_type, (None, None))[0]
    return result

def get_hint_name(hint_type: str) -> Optional[str]:
    """
    Get display name for a hint type.
    
    Args:
        hint_type: Hint type string
        
    Returns:
        str: Display name for the hint type or None if not found
    """
    result = HINT_TYPE_MAP.get(hint_type, (None, None))[1]
    return result

def get_hint_short(hint_type: str) -> Optional[str]:
    result = HINT_TYPE_MAP.get(hint_type, (None, None))[2]
    return result

def get_hint_icon(hint_type: str) -> str:
    """
    Get icon for a hint type.
    
    Args:
        hint_type: Hint type string
        
    Returns:
        str: Icon for the hint type or default icon if not found
    """
    result = HINT_ICONS.get(hint_type, "ℹ️")
    return result

def get_all_hint_types() -> List[str]:
    """
    Get list of all hint types.
    
    Returns:
        List[str]: List of hint type strings
    """
    return HINT_ORDER

def get_hint_setting_key(hint_type: str) -> Optional[str]:
    """
    Get setting key for a hint type.
    
    Args:
        hint_type: Hint type string
        
    Returns:
        str: Setting key for the hint type or None if not found
    """
    return HINT_SETTINGS_MAP.get(hint_type)

def get_hint_setting_name(setting_key: str) -> Optional[str]:
    """
    Get display name for a hint setting.
    
    Args:
        setting_key: Setting key string
        
    Returns:
        str: Display name for the setting or None if not found
    """
    return ALL_SETTINGS_NAMES.get(setting_key)

def is_hint_enabled(hint_type: str, settings: Dict) -> bool:
    """
    Check if a specific hint type is enabled in settings.
    
    Args:
        hint_type: Hint type string
        settings: User settings dictionary
        
    Returns:
        bool: True if hint is enabled, False otherwise
    """
    setting_key = get_hint_setting_key(hint_type)
    if not setting_key:
        return True  # Default to enabled if setting not found
    
    return settings.get(setting_key, True)  # Default to True

def get_enabled_hint_types(settings: Dict) -> List[str]:
    """
    Get list of enabled hint types based on settings.
    
    Args:
        settings: User settings dictionary
        
    Returns:
        List[str]: List of enabled hint type strings
    """
    enabled_hints = []
    for hint_type in HINT_ORDER:
        if is_hint_enabled(hint_type, settings):
            enabled_hints.append(hint_type)
    return enabled_hints

def format_hint_button(hint_type: str, has_hint: bool = False, is_active: bool = False, is_enabled: bool = True) -> str:
    """
    Format button text for a hint type.
    
    Args:
        hint_type: Hint type string
        has_hint: Whether hint exists
        is_active: Whether hint is currently active
        is_enabled: Whether hint type is enabled in settings
        
    Returns:
        str: Formatted button text
    """
    icon = get_hint_icon(hint_type)
    name = get_hint_name(hint_type)
    
    if not name:
        name = hint_type.capitalize()
    
    # If disabled in settings, show as disabled
    if not is_enabled:
        return f"🚫 {icon} {name}: Отключено"
    
    if has_hint:
        if is_active:
            # Подсказка активна (показывается)
            return f"✓ {icon} {name}: ✏️"
        else:
            # Подсказка есть, но не активна
            return f"{icon} {name}: 👁️"
    else:
        # Подсказки нет
        return f"{icon} {name}: ➕"

def has_hint(word_data: Dict, hint_type: str) -> bool:
    """
    Check if word data has a specific hint.
    
    Args:
        word_data: Word data dictionary
        hint_type: Hint type string
        
    Returns:
        bool: True if hint exists, False otherwise
    """
    hint_key = get_hint_key(hint_type)
    
    if not hint_key:
        return False
    
    # Check main word data
    if hint_key in word_data and word_data[hint_key]:
        return True
    
    # Check user_word_data if exists
    user_word_data = word_data.get("user_word_data", {})
    if user_word_data and hint_key in user_word_data and user_word_data[hint_key]:
        return True
    
    return False

def get_hints_from_word_data(word_data: Dict) -> Dict[str, str]:
    """
    Extract hints from word data.
    
    Args:
        word_data: Word data dictionary
        
    Returns:
        Dict[str, str]: Dictionary with hint types and values
    """
    hints = {}
    
    # Check main word data and user_word_data
    for hint_type, (hint_key, _) in HINT_TYPE_MAP.items():
        # Check in main word data
        if hint_key in word_data and word_data[hint_key]:
            hints[hint_type] = word_data[hint_key]
            continue
            
        # Check in user_word_data
        user_word_data = word_data.get("user_word_data", {})
        if user_word_data and hint_key in user_word_data and user_word_data[hint_key]:
            hints[hint_type] = user_word_data[hint_key]
    
    return hints

# Функции для работы с картинками написания
def is_writing_images_enabled(settings: Dict) -> bool:
    """
    Check if writing images are enabled in settings.
    
    Args:
        settings: User settings dictionary
        
    Returns:
        bool: True if writing images are enabled, False otherwise
    """
    return settings.get("show_writing_images", True)  # Default to True

def get_writing_image_setting_name(setting_key: str) -> Optional[str]:
    """
    Get display name for a writing image setting.
    
    Args:
        setting_key: Setting key string
        
    Returns:
        str: Display name for the setting or None if not found
    """
    return WRITING_IMAGE_SETTINGS_NAMES.get(setting_key)

def format_writing_image_button(has_image: bool = False, is_enabled: bool = True) -> str:
    """
    Format button text for writing image.
    
    Args:
        has_image: Whether writing image exists
        is_enabled: Whether writing images are enabled in settings
        
    Returns:
        str: Formatted button text
    """
    icon = "🖼️"
    name = "Картинка написания"
    
    if not is_enabled:
        return f"🚫 {icon} {name}: Отключено"
    
    if has_image:
        return f"{icon} {name}: 👁️"
    else:
        return f"{icon} {name}: ➕"
    