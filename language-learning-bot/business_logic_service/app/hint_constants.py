"""
Constants and mapping utilities for hint management.
UPDATED: Added individual hint settings constants.
UPDATED: Added writing images settings constants.
UPDATED: Removed hieroglyphic language restrictions - writing images are now controlled by user settings only.
"""

import sys
from pathlib import Path
from typing import Dict, Tuple
import logging

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
from common.hint_catalog import HINT_ORDER, HINT_UI

# Configure logger
logger = logging.getLogger(__name__)

# Словарь соответствия типов подсказок их API ключам и отображаемым именам
HINT_TYPE_MAP: Dict[str, Tuple[str, str, str]] = {
    "meaning": ("hint_meaning", "Ассоциация на русском", "(рус)"),
    "phoneticassociation": ("hint_phoneticassociation", "Ассоциация для фонетики", "(фонетик)"),
    "phoneticsound": ("hint_phoneticsound", "Звучание по слогам", "(звук)"),
    "writing": ("hint_writing", "Ассоциация для написания", "(запись)"),
}

# Иконки для разных типов подсказок
HINT_ICONS: Dict[str, str] = {ht: HINT_UI[ht][0] for ht in HINT_ORDER}

# Маппинг типов подсказок к их настройкам
HINT_SETTINGS_MAP: Dict[str, str] = {
    "meaning": "show_hint_meaning",
    "phoneticassociation": "show_hint_phoneticassociation",
    "phoneticsound": "show_hint_phoneticsound",
    "writing": "show_hint_writing"
}

# Все ключи настроек подсказок
HINT_SETTING_KEYS = list(HINT_SETTINGS_MAP.values())

# Логирование констант при загрузке модуля для отладки
logger.info(f"Loaded hint types: {list(HINT_TYPE_MAP.keys())}")
logger.info(f"Loaded hint icons: {HINT_ICONS}")
logger.info(f"Loaded hint settings: {HINT_SETTING_KEYS}")
