"""
Builds Telegram inline keyboards from BLS card.buttons.
No button logic here — BLS decides which buttons exist and what they do.
"""

from typing import Dict, Any, List
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


def build_card_keyboard(card: Dict[str, Any], language_id: str) -> InlineKeyboardMarkup:
    """Convert card.buttons list to InlineKeyboardMarkup, with optional sound and hint buttons."""
    builder = InlineKeyboardBuilder()
    for btn in card.get("buttons", []):
        cb = _callback(btn, language_id)
        builder.button(text=btn["text"], callback_data=cb)

    # Sound buttons only shown BEFORE answer — after reveal they've already been sent
    # as individual audio messages and stay visible in the chat.
    sounds = card.get("sounds") or []
    if sounds and not card.get("show_answer"):
        numbered = len(sounds) > 1
        for i, _ in enumerate(sounds):
            label = f"🔊 {i + 1}" if numbered else "🔊"
            builder.button(text=label, callback_data=f"study:{language_id}:sound:{i}")

    # Show hint management button only when answer is revealed, word_id is set,
    # and at least one hint type is enabled in user settings.
    meta = card.get("meta") or {}
    word_id = meta.get("word_id", "")
    hint_enabled = bool(meta.get("hint_enabled_types"))
    if card.get("show_answer") and word_id and hint_enabled:
        builder.button(text="💡 Подсказки", callback_data=f"hint:{language_id}:{word_id}:show")

    builder.adjust(2, repeat=True)
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


def build_welcome_keyboard(web_url: str = "") -> InlineKeyboardMarkup:
    """Navigation keyboard shown after the stats block in /start."""
    builder = InlineKeyboardBuilder()
    builder.button(text="🌐 Выбрать язык",  callback_data="welcome:language")
    builder.button(text="📊 Статистика",    callback_data="welcome:stats")
    builder.button(text="📱 Android",       callback_data="welcome:android")
    builder.button(text="💡 О подсказках",  callback_data="welcome:hints")
    builder.button(text="📚 Помощь",        callback_data="welcome:help")
    if web_url:
        builder.button(text="🔗 Веб-версия", url=web_url)
    builder.adjust(2)
    return builder.as_markup()


def _callback(btn: Dict[str, Any], language_id: str) -> str:
    btn_id = btn["id"]
    if btn_id == "rate":
        return f"study:{language_id}:rate:{btn['rating']}"
    return f"study:{language_id}:{btn_id}"
