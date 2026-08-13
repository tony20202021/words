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

    if show_answer and not session.get("prerendered"):
        # Плашка значит «ты знал это слово, а сейчас не вспомнил»: она держится
        # на score_changed, то есть на том, ЧТО пользователь нажал. В офлайн-партии
        # ответная сторона рисуется заранее, одна на оба исхода, и там
        # score_changed всегда False — плашка вылезала и после «Знаю», где онлайн
        # её прячет. Показать неверно хуже, чем не показать: пропущенная подсказка
        # ничего не портит, а ложная сообщает о провале, которого не было.
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
        _add_after_answer(content, word, settings, extra_content, words_studied,
                          session.get("language_name_ru", ""))
        _add_hints(content, word, uwd, settings)
        sounds = all_sounds
        buttons = _buttons_after(is_skipped, score_changed, show_skip,
                                 session.get("last_wrong_distractor_id"))

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
        # Кнопки пик-режима — тоже отсюда. Раньше карточка отдавала обычные
        # know/show_answer/skip, а каждый клиент выбрасывал buttons[] целиком и
        # рисовал свою «❓ Не знаю». Вместе с массивом терялась и «Пропускать»:
        # настройка show_skip_button в пик-режиме молча не работала ни в одном
        # из трёх клиентов, и снять пометку «пропущено» было нечем.
        buttons = _buttons_pick(is_skipped, show_skip)

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

def primary_meaning(translation: str) -> str:
    """
    Первое значение перевода — без пометок о других чтениях.

    У омографов перевод многострочный: основное значение, а ниже строка
    «⚠ то же написание читается иначе: …». В подсказке-вопросе и в вариантах
    пик-режима её показывать нельзя — она содержит вторую огласовку и просто
    выдаёт ответ.
    """
    return (translation or "").split("\n", 1)[0].strip()


def _add_before_answer(content: list, word: dict, show_mode: str) -> None:
    if show_mode == "translation":
        content.append({"type": "label", "text": "🔍 Слово на русском:"})
        # Только основное значение: полный перевод с другими чтениями
        # показывается уже на ответной стороне.
        content.append({"type": "translation", "text": primary_meaning(word.get("translation", ""))})
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


POS_FULL = {
    "сущ": "существительное", "глаг": "глагол", "прил": "прилагательное",
    "нареч": "наречие", "предл": "предлог", "мест": "местоимение",
    "числ": "числительное", "союз": "союз", "част": "частица",
    "межд": "междометие",
}


def _grammar_note(word: dict) -> str:
    """
    Строка с частью речи и словарной формой.

    Обе величины уже были собраны при подготовке словаря, но до карточки не
    доезжали. Для иврита это особенно полезно: одни и те же согласные бывают и
    существительным, и глаголом, и часть речи снимает половину неоднозначности.
    Словарную форму показываем только когда она отличается от самого слова —
    иначе это шум.
    """
    parts = []
    pos = (word.get("part_of_speech") or "").strip()
    if pos:
        parts.append(POS_FULL.get(pos, pos))
    lemma = (word.get("lemma") or "").strip()
    bare = _strip_niqqud(word.get("word_foreign") or "")
    if lemma and lemma != bare:
        parts.append(f"словарная форма: {lemma}")
    return " · ".join(parts)


def _strip_niqqud(text: str) -> str:
    import unicodedata
    return "".join(c for c in unicodedata.normalize("NFD", text)
                   if unicodedata.category(c) != "Mn")


# Поля tones/references/radicals заводились под китайский, но решают задачи,
# которые есть и в других языках — меняется только чем письмо неоднозначно.
# Поэтому подпись блока зависит от языка, а сами поля переиспользуются.
#   китайский: одна транскрипция, разные тоны -> разные слова
#   иврит:     одни согласные, разная огласовка -> разные слова
# То же с ссылками: у китайского это слова из тех же иероглифов, у иврита —
# слова того же корня.
EXTRA_LABELS_DEFAULT = {
    "tones": "🎵 Тоны:",
    "references": "🔍 Ссылки:",
    "radicals": "🔍 Радикалы:",
}
EXTRA_LABELS_BY_LANGUAGE = {
    "Иврит": {
        "tones": "🔤 То же написание с другой огласовкой:",
        "references": "🌱 Слова с той же основой:",
    },
}


def _extra_label(language_ru: str, key: str) -> str:
    per_language = EXTRA_LABELS_BY_LANGUAGE.get(language_ru or "", {})
    return per_language.get(key) or EXTRA_LABELS_DEFAULT[key]


def _add_after_answer(content: list, word: dict, settings: dict, extra: list,
                      words_studied: int = 0, language_ru: str = "") -> None:
    content.append({"type": "label", "text": "🔍 Перевод:"})
    content.append({"type": "translation", "text": word.get("translation", "")})
    if word.get("transcription"):
        content.append({"type": "label", "text": "🔊 Транскрипция:"})
        content.append({"type": "transcription", "text": f"[{word.get('transcription')}]"})
    content.append({"type": "label", "text": "📝 Слово на иностранном:"})
    content.append({"type": "foreign", "text": word.get("word_foreign", "")})
    # Часть речи и словарная форма — тип label, потому что его рисуют все три
    # клиента; новый тип пришлось бы добавлять в каждый.
    grammar = _grammar_note(word)
    if grammar:
        content.append({"type": "label", "text": f"📚 {grammar}"})
    if settings.get("show_tones") and (word.get("tones") or "").strip():
        tones = _filter_refs(word.get("tones", ""), words_studied)
        if tones.strip():
            extra.append({"type": "label", "text": _extra_label(language_ru, "tones"), "group": "tones"})
            extra.append({"type": "extra", "text": tones, "group": "tones"})
    if settings.get("show_references") and (word.get("references") or "").strip():
        refs = _filter_refs(word.get("references", ""), words_studied)
        if refs.strip():
            extra.append({"type": "label", "text": _extra_label(language_ru, "references"), "group": "references"})
            extra.append({"type": "extra", "text": refs, "group": "references"})
    if settings.get("show_radicals") and (word.get("radicals") or "").strip():
        extra.append({"type": "label", "text": _extra_label(language_ru, "radicals"), "group": "radicals"})
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
    """
    Вопросная сторона: только «знаю» и «не знаю».

    «Пропускать» здесь не место. Решение исключить слово принимают, УВИДЕВ его
    целиком — с переводом и произношением, — а на вопросной стороне перевода нет.
    Кнопка там же путала: она появлялась на одних словах и не появлялась на
    других (пик-режим включается случайно), и это выглядело как зависимость от
    прошлого ответа. Теперь она живёт на экране ответа и всегда.

    show_skip остаётся в сигнатуре: вызывающий код общий с _buttons_after, и
    выкидывать параметр ради двух строк значило бы разводить их сигнатуры.
    """
    return [
        {"id": "know", "text": "✅ Знаю", "style": "success", **_offline("record_and_reveal", "know")},
        {"id": "show_answer", "text": "❓ Не знаю", "style": "outline-danger", **_offline("reveal_answer")},
    ]


def _buttons_pick(is_skipped: bool, show_skip: bool = True) -> List[Dict[str, Any]]:
    """
    Кнопки вопросной стороны в пик-режиме.

    Сами варианты лежат в pick_options — здесь только «не знаю» и, если включена
    настройка, «Пропускать».

    id=pick_dont_know, а не show_answer: это pick_answer с
    selected_word_id="dont_know", то есть ответ ЗАСЧИТЫВАЕТСЯ как незнание, а
    клиент дополнительно показывает баннер из pick_answer_result. Обычный
    show_answer ничего не записывает — перепутав их, клиент потерял бы оценку.
    """
    return [{"id": "pick_dont_know", "text": "❓ Не знаю", "style": "outline-secondary",
             **_offline("record_and_reveal", "dont_know")}]


def _buttons_after(is_skipped: bool, score_changed: bool, show_skip: bool = True,
                   ban_distractor_id: str = None) -> List[Dict[str, Any]]:
    """
    Ответная сторона: переход дальше, «Пропускать» и — в пик-режиме — запрет
    комбинации.

    Запрет показывается, только когда есть ЧТО запрещать: конкретный вариант,
    который сбил с толку. После верного ответа такого варианта нет, и после
    «не знаю» тоже — там учащегося никто не путал.
    """
    skip_btn = _skip_button(is_skipped)
    ban_btn = ({"id": "ban_pair", "text": "🚫 Не показывать такую комбинацию",
                "style": "outline-warning", "bad_word_id": ban_distractor_id}
               if ban_distractor_id else None)
    if score_changed:
        # Оценка уже записана кнопкой know — здесь только переход, иначе
        # офлайн запишет результат дважды.
        btns = [{"id": "rate", "text": "✅ К следующему слову", "style": "success",
                 "rating": "know", **_offline("advance")}]
        # «Ой, все-таки не знаю» показываем всегда, когда слово засчитано знакомым,
        # включая верный ответ в пик-режиме. Раньше там кнопку прятали, и отменить
        # угаданный вариант было нечем: слово уходило как выученное и интервал
        # повторения растягивался. В режиме выбора из N вариантов угадать легко,
        # так что возможность отменить нужна там даже больше, чем при обычном вводе.
        btns.append({"id": "reconsider", "text": "❌ Ой, все-таки не знаю",
                     "style": "outline-danger", **_offline("reveal_question")})
        if show_skip:
            btns.append(skip_btn)
        if ban_btn:
            btns.append(ban_btn)
        return btns
    btns = [{"id": "rate", "text": "➡️ Дальше", "style": "success",
             "rating": "dont_know", **_offline("submit", "dont_know")}]
    if show_skip:
        btns.append(skip_btn)
    if ban_btn:
        btns.append(ban_btn)
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
