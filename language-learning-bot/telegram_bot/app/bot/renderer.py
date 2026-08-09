"""
Renders a BLS card dict into Telegram-safe HTML text.
No display logic here — just formatting of what BLS already decided.
"""

import logging
from html import escape
from typing import Dict, Any

logger = logging.getLogger(__name__)


def _esc(item: Dict[str, Any]) -> str:
    """
    Текст из базы — не разметка.

    Сообщение уходит с parse_mode="HTML", а слова, переводы и подсказки приходят
    из БД и от пользователя. Символ < или & в них ломал разбор — Telegram
    отвечал ошибкой и карточка не показывалась вовсе, — а сочетание вроде
    <b> подменяло оформление.

    Тип "extra" НЕ экранируется намеренно: варианты огласовки и однокоренные
    card_builder отдаёт уже с <b>/<i>, это его разметка, а не пользовательский
    ввод.
    """
    return escape(item.get("text") or "", quote=False)


def forbidden_pairs_count(card: Dict[str, Any]) -> int:
    """Сколько комбинаций забанено для текущего слова (0 — если ни одной)."""
    for item in card.get("extra_content") or []:
        if item.get("type") == "forbidden_quiz_pairs":
            return len(item.get("word_ids") or [])
    return 0


_ITEM_RENDERERS = {
    "label":         lambda i: f"\n{_esc(i)}",
    "foreign":       lambda i: f"<b>{_esc(i)}</b>",
    "transcription": lambda i: f"<b>{_esc(i)}</b>",
    "translation":   lambda i: f"<b>{_esc(i)}</b>",
    "hint":          lambda i: f"<i>{_esc(i)}</i>",
    "notice":        lambda i: _esc(i),
    "extra":         lambda i: i["text"],
    # card_builder кладёт сюда список запрещённых дистракторов (без "text").
    # Пока рендерера не было, блок молча пропадал: пользователь Telegram не
    # видел, что запреты копятся, и не мог их снять.
    "forbidden_quiz_pairs":
        lambda i: f"🚫 Запрещённые варианты в режиме выбора: {len(i.get('word_ids') or [])}",
}

# Типы, с которых начинается новое сообщение в extra_content: label открывает
# очередную группу, а forbidden_quiz_pairs приходит отдельным блоком в конце и
# не должен приклеиваться к предыдущей группе.
_BLOCK_START_TYPES = {"label", "forbidden_quiz_pairs"}


def render_card_text(card: Dict[str, Any]) -> str:
    """Convert card.content items to Telegram HTML text with a meta header.
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
        else:
            _warn_unknown_type(item)

    return "\n".join(lines).strip()


def _warn_unknown_type(item: Dict[str, Any]) -> None:
    """Расхождение с card_builder не должно проходить молча — иначе новый тип
    просто исчезает с экрана, как это случилось с forbidden_quiz_pairs."""
    logger.warning("renderer: неизвестный тип элемента карточки %r — пропущен",
                   item.get("type", ""))


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
            _warn_unknown_type(item)
            continue
        chunk = renderer(item)

        if item.get("type") in _BLOCK_START_TYPES:
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

    if not name_ru and not word_number:
        return ""

    lines = []

    if name_ru:
        lang_label = f"{name_ru} ({name_foreign})" if name_foreign else name_ru
        lines.append(f"📝 Язык: <b>{lang_label}</b>")

    if word_number:
        lines.append(f"\nСлово номер: <b>{word_number}</b> / <b>{words_studied}</b> / <b>{total_words}</b>")
        if meta.get("is_new_word") and meta.get("new_word_label"):
            lines.append(meta["new_word_label"])

    correct = meta.get("correct_count", 0)
    incorrect = meta.get("incorrect_count", 0)

    if meta.get("show_session_counter") and meta.get("session_counter_text"):
        lines.append(meta["session_counter_text"])

    done = (meta.get("session_pos", 1) - 1)

    if done > 0 or correct > 0 or incorrect > 0:
        lines.append(f"(правильных: {correct}, ошибок: {incorrect})")

    return "\n".join(lines)
