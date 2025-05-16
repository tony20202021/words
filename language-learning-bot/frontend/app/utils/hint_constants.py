"""
Constants and mapping utilities for hint management.
"""

from typing import Dict, Tuple, List, Optional
import logging

# Configure logger
logger = logging.getLogger(__name__)

# Словарь соответствия типов подсказок их API ключам и отображаемым именам
HINT_TYPE_MAP: Dict[str, Tuple[str, str]] = {
    "meaning": ("hint_meaning", "Ассоциация для значения на русском"),
    "phoneticassociation": ("hint_association", "Ассоциация для фонетики"),
    "phoneticsound": ("hint_syllables", "Фонетическое звучание"),
    "writing": ("hint_writing", "Ассоциация для написания")
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
    "hint_syllables": "phoneticsound",
    "hint_association": "phoneticassociation",
    "hint_meaning": "meaning",
    "hint_writing": "writing"
}

# Логирование констант при загрузке модуля для отладки
logger.info(f"Loaded hint types: {list(HINT_TYPE_MAP.keys())}")
logger.info(f"Loaded hint icons: {HINT_ICONS}")

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

def format_hint_button(hint_type: str, has_hint: bool = False, is_active: bool = False) -> str:
    """
    Format button text for a hint type.
    
    Args:
        hint_type: Hint type string
        has_hint: Whether hint exists
        is_active: Whether hint is currently active
        
    Returns:
        str: Formatted button text
    """
    icon = get_hint_icon(hint_type)
    name = get_hint_name(hint_type)
    
    if not name:
        name = hint_type.capitalize()
    
    if has_hint:
        if is_active:
            # Подсказка активна (показывается)
            return f"✓ {icon} {name}: ✏️ Редактировать"
        else:
            # Подсказка есть, но не активна
            return f"{icon} {name}: 👁️ Показать"
    else:
        # Подсказки нет
        return f"{icon} {name} (отсутствует): ➕ Создать"

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