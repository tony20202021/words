"""
Card builder — sole place that decides what a study card shows and which buttons appear.
Clients (web, Telegram) render whatever this returns; they contain no display logic.
"""

import json
import re
from typing import Any, Dict, List
from app.hint_constants import HINT_ORDER, HINT_SETTINGS_MAP, HINT_ICONS, HINT_TYPE_MAP


def build_card(session: Dict[str, Any], word: Dict[str, Any], show_answer: bool) -> Dict[str, Any]:
    """Build a display card for the current word + session state."""
    show_mode = session.get("show_mode", "foreign")
    uwd = (word or {}).get("user_word_data") or {}
    score = uwd.get("score", -1)
    interval = uwd.get("check_interval", 0)
    next_check_date = (uwd.get("next_check_date") or "")
    is_skipped = uwd.get("is_skipped", False)
    score_changed = session.get("score_changed", False)

    # for the badge use pre-answer values so it shows what the user knew before
    badge_score = session.get("prev_score", score) if show_answer else score
    badge_interval = session.get("prev_interval", interval) if show_answer else interval
    badge_next_date = session.get("prev_next_check_date", next_check_date) if show_answer else next_check_date
    settings = session.get("settings") or {}

    all_sounds = _parse_sound_urls(word) if settings.get("show_sounds", True) else []

    content: List[Dict[str, Any]] = []

    if is_skipped:
        content.append({"type": "notice", "variant": "secondary",
                         "text": "⏩ Статус: это слово помечено для пропуска."})

    if show_answer:
        if not score_changed and score == 1 and interval > 0:
            content.append({"type": "notice", "variant": "info",
                             "text": f"⏱ Вы знали это слово:\nПредыдущий интервал: {interval} дн."})

    session_words = session.get("words", [])
    session_current = session.get("current_index", 0)
    total_processed = session.get("total_words_processed", 0)
    # words_for_today covers all batches; batch calculation is fallback when not set
    session_total = session.get("words_for_today") or (total_processed + max(0, len(session_words) - session_current))

    extra_content: List[Dict[str, Any]] = []

    words_studied = session.get("words_studied", 0)

    if not show_answer:
        _add_before_answer(content, word, show_mode)
        sounds = all_sounds if show_mode == "sound" else []
        _add_hints(content, word, uwd, settings)
        buttons = _buttons_before(is_skipped)
    else:
        _add_after_answer(content, word, settings, extra_content, words_studied)
        _add_hints(content, word, uwd, settings)
        sounds = all_sounds
        buttons = _buttons_after(is_skipped, score_changed)

    big_word = None
    if show_answer and settings.get("show_big", False) and (word or {}).get("word_foreign"):
        big_word = {
            "word": word.get("word_foreign", ""),
            "transcription": word.get("transcription") or "",
        }

    hint_enabled_types = [ht for ht in HINT_ORDER if settings.get(HINT_SETTINGS_MAP[ht], False)]

    return {
        "show_answer": show_answer,
        "content": content,
        "extra_content": extra_content,
        "sounds": sounds,
        "buttons": buttons,
        "big_word": big_word,
        "meta": {
            "word_id": str((word or {}).get("_id") or (word or {}).get("id") or (word or {}).get("word_id") or ""),
            "hint_enabled_types": hint_enabled_types,
            "word_number": (word or {}).get("word_number"),
            "score": score,
            "interval": interval,
            "next_check_date": next_check_date[:10] if next_check_date else "",
            "is_skipped": is_skipped,
            "session_pos": total_processed + 1,
            "session_total": session_total,
            "correct_count": session.get("correct_count", 0),
            "incorrect_count": session.get("incorrect_count", 0),
            "result_history": session.get("result_history", []),
            "pending_result": ("know" if session.get("score_changed") else "dont_know") if show_answer else None,
            "score_badge": _score_badge(
                badge_score, badge_interval, badge_next_date,
                new_interval=interval if (show_answer and interval > 0) else 0,
                new_next_date=next_check_date if (show_answer and interval > 0) else "",
                new_score=score if show_answer else None,
            ),
            "language_name_ru": session.get("language_name_ru", ""),
            "language_name_foreign": session.get("language_name_foreign", ""),
            "words_studied": session.get("words_studied", 0),
            "total_words": session.get("total_words", 0),
            "words_for_today": session.get("words_for_today", 0),
        },
    }


# ── content builders ──────────────────────────────────────────────────────────

def _add_before_answer(content: list, word: dict, show_mode: str) -> None:
    if show_mode == "translation":
        content.append({"type": "label", "text": "🔍 Слово на русском:"})
        content.append({"type": "translation", "text": word.get("translation", "")})
    elif show_mode == "transcription":
        content.append({"type": "label", "text": "🔊 Транскрипция:"})
        content.append({"type": "transcription", "text": f"[{word.get('transcription', '')}]"})
    elif show_mode == "sound":
        content.append({"type": "label", "text": "🎧 Угадайте слово по звуку:", "align": "center"})
    else:
        content.append({"type": "label", "text": "📝 Слово на иностранном:"})
        content.append({"type": "foreign", "text": word.get("word_foreign", "")})


def _filter_refs(text: str, words_studied: int) -> str:
    """Filter out reference lines whose [#N] word number exceeds words_studied."""
    if words_studied <= 0:
        return text
    lines = text.split("\n")
    kept = []
    for line in lines:
        m = re.search(r"\[#(\d+)\]", line)
        if m and int(m.group(1)) > words_studied:
            continue
        kept.append(line)
    return "\n".join(kept)


def _add_after_answer(content: list, word: dict, settings: dict, extra: list,
                      words_studied: int = 0) -> None:
    content.append({"type": "label", "text": "🔍 Перевод:"})
    content.append({"type": "translation", "text": word.get("translation", "")})
    if word.get("transcription"):
        content.append({"type": "label", "text": "🔊 Транскрипция:"})
        content.append({"type": "transcription", "text": f"[{word.get('transcription')}]"})
    content.append({"type": "label", "text": "📝 Слово на иностранном:"})
    content.append({"type": "foreign", "text": word.get("word_foreign", "")})
    if settings.get("show_tones") and (word.get("tones") or "").strip():
        tones = _filter_refs(word.get("tones", ""), words_studied)
        if tones.strip():
            extra.append({"type": "label", "text": "🎵 Тоны:", "group": "tones"})
            extra.append({"type": "extra", "text": tones, "group": "tones"})
    if settings.get("show_references") and (word.get("references") or "").strip():
        refs = _filter_refs(word.get("references", ""), words_studied)
        if refs.strip():
            extra.append({"type": "label", "text": "🔍 Ссылки:", "group": "references"})
            extra.append({"type": "extra", "text": refs, "group": "references"})
    if settings.get("show_radicals") and (word.get("radicals") or "").strip():
        extra.append({"type": "label", "text": "🔍 Радикалы:", "group": "radicals"})
        extra.append({"type": "extra", "text": word.get("radicals"), "group": "radicals"})


def _add_hints(content: list, word: dict, uwd: dict, settings: dict) -> None:
    """Append hint content items for each enabled hint type that has a value."""
    for ht in HINT_ORDER:
        if not settings.get(HINT_SETTINGS_MAP[ht], False):
            continue
        field = HINT_TYPE_MAP[ht][0]           # e.g. "hint_meaning"
        icon  = HINT_ICONS.get(ht, "💡")
        val   = (uwd.get(field) or "").strip() or (word.get(field) or "").strip()
        if val:
            content.append({"type": "hint", "text": f"{icon} {val}"})


# ── buttons ───────────────────────────────────────────────────────────────────

def _buttons_before(is_skipped: bool) -> List[Dict[str, Any]]:
    return [
        {"id": "know", "text": "✅ Знаю", "style": "success"},
        {"id": "show_answer", "text": "❓ Не знаю", "style": "outline-danger"},
        {"id": "toggle_skip",
         "text": "⏩ Не пропускать" if is_skipped else "⏩ Пропускать",
         "style": "outline-secondary"},
    ]


def _buttons_after(is_skipped: bool, score_changed: bool) -> List[Dict[str, Any]]:
    skip_btn = {
        "id": "toggle_skip",
        "text": "⏩ Не пропускать" if is_skipped else "⏩ Пропускать",
        "style": "outline-secondary",
    }
    if score_changed:
        return [
            {"id": "rate", "text": "✅ К следующему слову", "style": "success", "rating": "know"},
            {"id": "reconsider", "text": "❌ Ой, все-таки не знаю", "style": "outline-danger"},
            skip_btn,
        ]
    return [
        {"id": "rate", "text": "➡️ Дальше", "style": "success", "rating": "dont_know"},
        skip_btn,
    ]


# ── badge ─────────────────────────────────────────────────────────────────────

def _score_badge(score: int, interval: int, next_check_date: str,
                 new_interval: int = 0, new_next_date: str = "",
                 new_score: int = None) -> Dict[str, Any]:
    if score == 1:
        badge: Dict[str, Any] = {
            "text": f"✓ знал · {interval}д",
            "variant": "success",
            "next_date": next_check_date[:10] if next_check_date else "",
        }
    elif score == 0:
        badge = {"text": "✗ не знал", "variant": "danger", "next_date": ""}
    else:
        badge = {"text": "новое", "variant": "secondary", "next_date": ""}
    if new_interval and new_next_date:
        badge["new_interval"] = new_interval
        badge["new_next_date"] = new_next_date[:10]
        badge["new_variant"] = (
            "success" if new_score == 1 else
            "danger" if new_score == 0 else
            "secondary"
        )
    return badge


# ── sounds ────────────────────────────────────────────────────────────────────

def _parse_sound_urls(word: dict) -> List[str]:
    raw = (word or {}).get("sounds")
    if not raw:
        return []
    try:
        data = json.loads(raw)
        if isinstance(data, str):
            data = json.loads(data)
        return [data[k] for k in sorted(data.keys()) if data[k]]
    except Exception:
        return []
