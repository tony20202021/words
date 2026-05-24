"""
Card builder — sole place that decides what a study card shows and which buttons appear.
Clients (web, Telegram) render whatever this returns; they contain no display logic.
"""

import json
from typing import Any, Dict, List


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

    if not show_answer and score == 1 and interval > 0:
        content.append({"type": "notice", "variant": "info",
                         "text": f"⏱ Вы знали это слово:\nПредыдущий интервал: {interval} дн."})

    if show_answer:
        if score_changed and score == 1 and interval > 0:
            content.append({"type": "notice", "variant": "success",
                             "text": f"Следующий интервал: {interval} дн."})
        elif not score_changed and score == 1 and interval > 0:
            content.append({"type": "notice", "variant": "info",
                             "text": f"⏱ Вы знали это слово:\nПредыдущий интервал: {interval} дн."})

    session_words = session.get("words", [])
    session_current = session.get("current_index", 0)
    total_processed = session.get("total_words_processed", 0)
    session_total = total_processed + max(0, len(session_words) - session_current)

    extra_content: List[Dict[str, Any]] = []

    if not show_answer:
        _add_before_answer(content, word, show_mode)
        sounds = all_sounds if show_mode == "sound" else []
        _add_hints(content, word, uwd)
        buttons = _buttons_before(is_skipped)
    else:
        _add_after_answer(content, word, settings, extra_content)
        _add_hints(content, word, uwd)
        sounds = all_sounds
        buttons = _buttons_after(is_skipped, score_changed)

    big_word = None
    if show_answer and settings.get("show_big", False) and (word or {}).get("word_foreign"):
        big_word = {
            "word": word.get("word_foreign", ""),
            "transcription": word.get("transcription") or "",
        }

    return {
        "show_answer": show_answer,
        "content": content,
        "extra_content": extra_content,
        "sounds": sounds,
        "buttons": buttons,
        "big_word": big_word,
        "meta": {
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
            "score_badge": _score_badge(badge_score, badge_interval, badge_next_date),
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


def _add_after_answer(content: list, word: dict, settings: dict, extra: list) -> None:
    content.append({"type": "label", "text": "🔍 Перевод:"})
    content.append({"type": "translation", "text": word.get("translation", "")})
    if word.get("transcription"):
        content.append({"type": "label", "text": "🔊 Транскрипция:"})
        content.append({"type": "transcription", "text": f"[{word.get('transcription')}]"})
    content.append({"type": "label", "text": "📝 Слово на иностранном:"})
    content.append({"type": "foreign", "text": word.get("word_foreign", "")})
    # Order matches old bot: tones → references → radicals
    if settings.get("show_tones") and (word.get("tones") or "").strip():
        extra.append({"type": "label", "text": "🎵 Тоны:"})
        extra.append({"type": "extra", "text": word.get("tones")})
    if settings.get("show_references") and (word.get("references") or "").strip():
        extra.append({"type": "label", "text": "🔍 Ссылки:"})
        extra.append({"type": "extra", "text": word.get("references")})
    if settings.get("show_radicals") and (word.get("radicals") or "").strip():
        extra.append({"type": "label", "text": "🔍 Радикалы:"})
        extra.append({"type": "extra", "text": word.get("radicals")})


def _add_hints(content: list, word: dict, uwd: dict) -> None:
    meaning = uwd.get("hint_meaning") or word.get("hint_meaning")
    phonetic = uwd.get("hint_phoneticsound") or word.get("hint_phoneticsound")
    if meaning:
        content.append({"type": "hint", "text": f"💡 {meaning}"})
    if phonetic:
        content.append({"type": "hint", "text": f"🔊 {phonetic}"})


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

def _score_badge(score: int, interval: int, next_check_date: str) -> Dict[str, Any]:
    if score == 1:
        return {
            "text": f"✓ знал · {interval}д",
            "variant": "success",
            "next_date": next_check_date[:10] if next_check_date else "",
        }
    if score == 0:
        return {"text": "✗ не знал", "variant": "danger", "next_date": ""}
    return {"text": "новое", "variant": "secondary", "next_date": ""}


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
