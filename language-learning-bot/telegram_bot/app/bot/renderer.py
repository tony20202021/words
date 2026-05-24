"""
Renders a BLS card dict into Telegram-safe HTML text.
No display logic here — just formatting of what BLS already decided.
"""

from typing import Dict, Any


_ITEM_RENDERERS = {
    "label":         lambda i: f"\n{i['text']}",
    "foreign":       lambda i: f"<b>{i['text']}</b>",
    "transcription": lambda i: f"<b>{i['text']}</b>",
    "translation":   lambda i: f"<b>{i['text']}</b>",
    "hint":          lambda i: f"<i>{i['text']}</i>",
    "notice":        lambda i: i["text"],
    "extra":         lambda i: i["text"],
}


def render_card_text(card: Dict[str, Any]) -> str:
    """Convert card.content items to Telegram HTML text with meta header and footer.
    Extra content (tones, references, radicals) is intentionally excluded — send via render_extra_texts()."""
    meta = card.get("meta") or {}
    lines = []

    header = _render_header(meta)
    if header:
        lines.append(header)

    for item in card.get("content", []):
        renderer = _ITEM_RENDERERS.get(item.get("type", ""))
        if renderer:
            lines.append(renderer(item))

    footer = _render_footer(meta)
    if footer:
        lines.append(f"\n<i>{footer}</i>")

    return "\n".join(lines).strip()


def render_extra_texts(card: Dict[str, Any]) -> list:
    """Return list of strings for extra_content (tones/references/radicals).
    Each label+content block is a separate message, like the old bot.
    Long content is split at 4000 chars. Returns [] if nothing to show."""
    extra = card.get("extra_content") or []
    if not extra:
        return []

    MAX = 4000
    messages = []
    current_block = ""

    for item in extra:
        renderer = _ITEM_RENDERERS.get(item.get("type", ""))
        if not renderer:
            continue
        chunk = renderer(item)

        if item.get("type") == "label":
            # Each label starts a new message block
            if current_block.strip():
                messages.append(current_block.strip())
            current_block = chunk
        else:
            # Content: append to current block, split if too long
            candidate = (current_block + "\n" + chunk) if current_block else chunk
            if len(candidate) > MAX:
                if current_block.strip():
                    messages.append(current_block.strip())
                # Split oversized content into chunks
                while len(chunk) > MAX:
                    messages.append(chunk[:MAX])
                    chunk = chunk[MAX:]
                current_block = chunk
            else:
                current_block = candidate

    if current_block.strip():
        messages.append(current_block.strip())

    return messages


def _render_header(meta: Dict[str, Any]) -> str:
    name_ru = meta.get("language_name_ru", "")
    name_foreign = meta.get("language_name_foreign", "")
    word_number = meta.get("word_number")
    words_studied = meta.get("words_studied", 0)
    total_words = meta.get("total_words", 0)
    session_pos = meta.get("session_pos", 1)
    words_for_today = meta.get("words_for_today", 0)

    if not name_ru and not word_number:
        return ""

    lines = []

    if name_ru:
        lang_label = f"{name_ru} ({name_foreign})" if name_foreign else name_ru
        lines.append(f"📝 Язык: <b>{lang_label}</b>")

    if word_number:
        lines.append(f"\nСлово номер: <b>{word_number}</b> / <b>{words_studied}</b> / <b>{total_words}</b>")
        if word_number > words_studied:
            lines.append("(новое слово, изучается первый раз)")

    correct = meta.get("correct_count", 0)
    incorrect = meta.get("incorrect_count", 0)
    done = (meta.get("session_pos", 1) - 1)

    # Use words_for_today (total due today) — like web and old bot, not session batch size
    if words_for_today and word_number and word_number <= words_studied:
        if session_pos >= words_for_today:
            lines.append(f"(завершающее в текущей сессии: <b>{session_pos}</b>)")
        else:
            lines.append(f"(изучается в текущей сессии: <b>{session_pos}</b> из <b>{words_for_today}</b>)")

    if done > 0 or correct > 0 or incorrect > 0:
        lines.append(f"(правильных: {correct}, ошибок: {incorrect})")

    return "\n".join(lines)


def _render_footer(meta: Dict[str, Any]) -> str:
    return ""
