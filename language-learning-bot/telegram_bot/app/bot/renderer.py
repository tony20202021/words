"""
Renders a BLS card dict into Telegram-safe HTML text.
No display logic here — just formatting of what BLS already decided.
"""

from typing import Dict, Any


_ITEM_RENDERERS = {
    "label":        lambda i: f"\n<b>{i['text']}</b>",
    "foreign":      lambda i: f"<code>{i['text']}</code>",
    "transcription": lambda i: f"<i>{i['text']}</i>",
    "translation":  lambda i: i["text"],
    "hint":         lambda i: f"<i>{i['text']}</i>",
    "notice":       lambda i: i["text"],
}


def render_card_text(card: Dict[str, Any]) -> str:
    """Convert card.content items to Telegram HTML text with meta footer."""
    lines = []

    for item in card.get("content", []):
        renderer = _ITEM_RENDERERS.get(item.get("type", ""))
        if renderer:
            lines.append(renderer(item))

    meta = card.get("meta") or {}
    footer = _render_footer(meta)
    if footer:
        lines.append(f"\n<i>{footer}</i>")

    return "\n".join(lines).strip()


def _render_footer(meta: Dict[str, Any]) -> str:
    parts = []

    word_num = meta.get("word_number")
    if word_num:
        parts.append(f"Слово: {word_num}")

    badge = meta.get("score_badge") or {}
    if badge.get("text"):
        parts.append(badge["text"])

    done = meta.get("session_pos", 1) - 1
    correct = meta.get("correct_count", 0)
    incorrect = meta.get("incorrect_count", 0)
    if done > 0 or correct > 0 or incorrect > 0:
        parts.append(f"✓{correct} ✗{incorrect}")

    return "  ·  ".join(parts)
