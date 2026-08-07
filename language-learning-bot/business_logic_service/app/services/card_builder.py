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

    unknown_limit = int(settings.get("unknown_limit_new_words", 10))
    word_number = (word or {}).get("word_number")
    restart_notice = None
    if (words_studied > 0 and word_number is not None and
            word_number >= words_studied and
            session.get("incorrect_count", 0) >= unknown_limit):
        restart_notice = (f"⚠️ Ошибок в сессии: {session.get('incorrect_count', 0)}, "
                          f"лимит: {unknown_limit}. "
                          "Рекомендуется перезапустить сессию и повторить слова с начала.")

    show_skip = settings.get("show_skip_button", True)
    if not show_answer:
        _add_before_answer(content, word, show_mode)
        sounds = all_sounds if show_mode == "sound" else []
        _add_hints(content, word, uwd, settings)
        buttons = _buttons_before(is_skipped, show_skip)
    else:
        _add_after_answer(content, word, settings, extra_content, words_studied)
        _add_hints(content, word, uwd, settings)
        sounds = all_sounds
        pick_answer_was_used = session.get("pick_answer_was_used", False)
        buttons = _buttons_after(is_skipped, score_changed, show_skip, pick_answer_was_used)

    big_word = None
    if show_answer and settings.get("show_big", False) and (word or {}).get("word_foreign"):
        big_word = {
            "word": word.get("word_foreign", ""),
            "transcription": word.get("transcription") or "",
        }

    hint_enabled_types = [ht for ht in HINT_ORDER if settings.get(HINT_SETTINGS_MAP[ht], False)]

    session_pos = total_processed + 1
    words_for_today_val = session.get("words_for_today", 0)
    is_new_word = bool(
        word_number is not None and words_studied > 0 and word_number > words_studied
    )
    show_session_counter = bool(
        word_number is not None and words_studied > 0
        and not is_new_word and words_for_today_val > 0
    )
    session_counter_text = ""
    if show_session_counter:
        if session_pos >= words_for_today_val:
            session_counter_text = f"(завершающее в текущей сессии: {session_pos})"
        else:
            session_counter_text = f"(в сессии: {session_pos} из {session_total})"

    quiz_options = session.get("quiz_options")
    pick_mode_active = session.get("pick_mode_active", False)

    # Show pick options only before the answer; after answer — show normal card
    pick_options = None
    if pick_mode_active and not show_answer and quiz_options:
        # Stamp each option with the rating an offline client should record —
        # so Android reads it straight from the bundle instead of re-deriving it.
        options = []
        for o in quiz_options.get("options", []):
            options.append({**o, "offline_rating": "know" if o.get("is_correct") else "dont_know"})
        pick_options = {
            "target_modality": quiz_options.get("target_modality", "foreign"),
            "options": options,
        }

    # Forbidden quiz pairs for this word — shown in extra_content after answer
    if show_answer:
        forbidden = ((word or {}).get("user_word_data") or {}).get("forbidden_quiz_pairs") or []
        if forbidden:
            extra_content.append({
                "type": "forbidden_quiz_pairs",
                "word_ids": forbidden,
                "group": "forbidden_quiz_pairs",
            })

    last_wrong_distractor_id = session.get("last_wrong_distractor_id") if show_answer else None
    pick_answer_result = session.get("pick_answer_result") if show_answer else None

    return {
        "show_answer": show_answer,
        "restart_notice": restart_notice,
        "content": content,
        "extra_content": extra_content,
        "sounds": sounds,
        "buttons": buttons,
        "big_word": big_word,
        "pick_options": pick_options,
        "last_wrong_distractor_id": last_wrong_distractor_id,
        "pick_answer_result": pick_answer_result,
        "meta": {
            "word_id": str((word or {}).get("_id") or (word or {}).get("id") or (word or {}).get("word_id") or ""),
            "hint_enabled_types": hint_enabled_types,
            "word_number": (word or {}).get("word_number"),
            "score": score,
            "interval": interval,
            "next_check_date": next_check_date[:10] if next_check_date else "",
            "is_skipped": is_skipped,
            "session_pos": session_pos,
            "session_total": session_total,
            "show_session_counter": show_session_counter,
            "session_counter_text": session_counter_text,
            "is_new_word": is_new_word,
            "new_word_label": "(новое слово, изучается первый раз)" if is_new_word else "",
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

# Offline action semantics per button — the single source of truth for how an
# offline client (Android) interprets each button without any of its own rules.
#
#   reveal_answer      показать ответную сторону, ничего не записывать
#   reveal_question    вернуться к вопросу (reconsider)
#   record_and_reveal  записать оценку и показать ответ, НЕ листать дальше
#   submit             записать оценку и перейти к следующему слову
#   advance            только перейти дальше, оценка уже записана
#
#   offline_rating: оценка для record_and_reveal и submit (иначе отсутствует)
#
# Пара know -> rate повторяет онлайн: know_word() показывает результат без
# перехода, а rate_word("know") затем листает и НЕ начисляет повторно. Если
# офлайн пометить know как submit, ответная карточка не покажется вовсе —
# пользователь увидит, что его перебрасывает сразу на следующее слово.
def _offline(effect: str, rating: str = None) -> Dict[str, Any]:
    d = {"offline_effect": effect}
    if rating is not None:
        d["offline_rating"] = rating
    return d


def _skip_button(is_skipped: bool) -> Dict[str, Any]:
    return {
        "id": "toggle_skip",
        "text": "⏩ Не пропускать" if is_skipped else "⏩ Пропускать",
        "style": "outline-secondary",
        **_offline("submit", "skip"),
    }


def _buttons_before(is_skipped: bool, show_skip: bool = True) -> List[Dict[str, Any]]:
    btns = [
        {"id": "know", "text": "✅ Знаю", "style": "success", **_offline("record_and_reveal", "know")},
        {"id": "show_answer", "text": "❓ Не знаю", "style": "outline-danger", **_offline("reveal_answer")},
    ]
    if show_skip:
        btns.append(_skip_button(is_skipped))
    return btns


def _buttons_after(is_skipped: bool, score_changed: bool, show_skip: bool = True,
                   pick_mode: bool = False) -> List[Dict[str, Any]]:
    skip_btn = _skip_button(is_skipped)
    if score_changed:
        # Оценка уже записана кнопкой know — здесь только переход, иначе
        # офлайн запишет результат дважды.
        btns = [{"id": "rate", "text": "✅ К следующему слову", "style": "success",
                 "rating": "know", **_offline("advance")}]
        if not pick_mode:
            btns.append({"id": "reconsider", "text": "❌ Ой, все-таки не знаю",
                         "style": "outline-danger", **_offline("reveal_question")})
        if show_skip:
            btns.append(skip_btn)
        return btns
    btns = [{"id": "rate", "text": "➡️ Дальше", "style": "success",
             "rating": "dont_know", **_offline("submit", "dont_know")}]
    if show_skip:
        btns.append(skip_btn)
    return btns


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
