"""Shared hint type order and UI labels — single source for BLS and all frontends."""

from typing import Dict, List, Tuple

HINT_ORDER: List[str] = [
    "meaning",
    "phoneticassociation",
    "phoneticsound",
    "writing",
]

# hint_type → (icon, label, settings_key)
HINT_UI: Dict[str, Tuple[str, str, str]] = {
    "meaning":             ("🧠", "Ассоциация (рус)", "show_hint_meaning"),
    "phoneticassociation": ("💡", "Ассоциация фонетики", "show_hint_phoneticassociation"),
    "phoneticsound":       ("🎵", "Звучание по слогам", "show_hint_phoneticsound"),
    "writing":             ("✍️", "Написание", "show_hint_writing"),
}


def hint_types_ordered() -> Dict[str, Tuple[str, str]]:
    """Return {type: (icon, label)} in canonical HINT_ORDER."""
    return {ht: (HINT_UI[ht][0], HINT_UI[ht][1]) for ht in HINT_ORDER}


def setting_key_for(hint_type: str) -> str:
    return HINT_UI[hint_type][2]
