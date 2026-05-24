"""
Builds Telegram inline keyboards from BLS card.buttons.
No button logic here — BLS decides which buttons exist and what they do.
"""

from typing import Dict, Any, List
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


def build_card_keyboard(card: Dict[str, Any], language_id: str) -> InlineKeyboardMarkup:
    """Convert card.buttons list to InlineKeyboardMarkup, with optional sound buttons."""
    builder = InlineKeyboardBuilder()
    for btn in card.get("buttons", []):
        cb = _callback(btn, language_id)
        builder.button(text=btn["text"], callback_data=cb)
    builder.adjust(2, repeat=True)

    sounds = card.get("sounds") or []
    if sounds:
        sound_builder = InlineKeyboardBuilder()
        for i in range(len(sounds)):
            label = f"🔊 {i + 1}" if len(sounds) > 1 else "🔊"
            sound_builder.button(text=label, callback_data=f"study:{language_id}:sound:{i}")
        sound_builder.adjust(len(sounds))
        builder.attach(sound_builder)

    return builder.as_markup()


def build_language_keyboard(languages: List[Dict[str, Any]]) -> InlineKeyboardMarkup:
    """One button per language for the /start language picker."""
    builder = InlineKeyboardBuilder()
    for lang in languages:
        name = lang.get("name_ru", "")
        foreign = lang.get("name_foreign", "")
        label = f"{name} ({foreign})" if foreign else name
        builder.button(text=label, callback_data=f"lang:{lang['id']}")
    builder.adjust(1)
    return builder.as_markup()


def _callback(btn: Dict[str, Any], language_id: str) -> str:
    btn_id = btn["id"]
    if btn_id == "rate":
        return f"study:{language_id}:rate:{btn['rating']}"
    return f"study:{language_id}:{btn_id}"
