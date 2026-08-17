#!/usr/bin/env python3
"""Снимает карточки с НАСТОЯЩЕГО card_builder и кладёт их в фикстуры для снимков.

Зачем не руками
---------------
Первый снимок экрана я собрал на выдуманной карточке — и она соврала: блоки
доп. информации я расположил в одном порядке, а клиент рисует их в своём
(radicals → references → tones). Пару минут я считал это дефектом клиента.

Выдуманные данные проверяют мои представления о сервере, а не сервер. Поэтому
карточки строит здесь тот же build_card, что и в бою, а снимки рисуются ровно
из того, что он вернул.

Запуск:
    python android/app/src/test/resources/make_card_fixtures.py
Результат:
    android/app/src/test/resources/cards/*.json
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "business_logic_service"))
sys.path.insert(0, ROOT)  # common/ лежит в корне и нужен hint_constants

from app.services.card_builder import build_card  # noqa: E402

OUT = os.path.join(HERE, "cards")

HEBREW_TONES = (
    "<b>עם</b>: <i>вариантов огласовки: 2</i>\n"
    " - <b>עִם</b> [ʔim]: с, вместе с\n"
    " - <b>עַם</b> [ʔam]: народ"
)
HEBREW_REFS = (
    "<b>עם</b>: <i>слов с этой основой: 3</i>\n"
    "<i>[#27]</i>אוֹתוֹ [ʔoˈto] его; тот самый\n"
    "<i>[#33]</i>אוֹתִי [ʔoˈti] меня\n"
    "<i>[#41]</i>עִמָּנוּ [ʔiˈmanu] с нами"
)


def session(**over):
    s = {
        "session_id": "s1", "user_id": "u1", "language_id": "l1",
        "show_mode": "foreign", "score_changed": False, "word_processed": False,
        "show_answer": False, "total_words_processed": 3,
        "correct_count": 2, "incorrect_count": 1,
        "result_history": ["know", "know", "dont_know"],
        "words_for_today": 10, "session_pos": 3, "session_total": 10,
        "words_studied": 500,
        # Без него подписи блоков уезжают в значения по умолчанию («Тоны:»,
        # «Ссылки:») — на первом снимке так и вышло, и я чуть не принял это за
        # дефект клиента.
        "language_name_ru": "Иврит",
        "settings": {"show_sounds": True, "show_tones": True,
                     "show_references": True, "show_skip_button": True},
    }
    s.update(over)
    return s


def word(**over):
    w = {
        "word_number": 15, "word_foreign": "עִם", "translation": "с, вместе с",
        "transcription": "ʔim", "part_of_speech": "предл", "lemma": "עם",
        "tones": HEBREW_TONES, "references": HEBREW_REFS, "sounds": None,
        "user_word_data": {"score": 1, "check_interval": 4,
                           "next_check_date": "2026-08-20", "is_skipped": False},
    }
    w.update(over)
    return w


def pick_session(**over):
    # show_mode обязан отличаться от target_modality: _choose_target_modality
    # это гарантирует. Сначала я поставил foreign/foreign — и на снимке вопрос
    # показывал ровно тот вариант, который надо выбрать. В бою так не бывает,
    # снимок изображал невозможное.
    return session(
        show_mode="translation",
        pick_mode_active=True,
        quiz_options={
            "target_modality": "foreign",
            "options": [
                {"word_id": "w1", "target_text": "עִם", "is_correct": True},
                {"word_id": "w2", "target_text": "אֲבָל", "is_correct": False},
                {"word_id": "w3", "target_text": "כְּמוֹ", "is_correct": False},
                {"word_id": "w4", "target_text": "בִּשְׁבִיל", "is_correct": False},
            ],
        },
        **over,
    )


# Отбор сценариев — по журналу дефектов: каждый снимок стоит на месте, где уже
# что-то ломалось, либо на краю, где ломается обычно (единица, длинный текст,
# спецсимволы разметки).
SOUNDS = "https://example.org/he/im_1.mp3"

CASES = {
    # Все варианты вопроса — по одному на каждый show_mode. Стороны вопроса
    # отличаются не только текстом: у звука нет ни слова, ни транскрипции,
    # только кнопка проигрывания, и вёрстка там своя.
    "question_foreign":       (session(show_mode="foreign"), word(), False),
    "question_translation":   (session(show_mode="translation"), word(), False),
    "question_transcription": (session(show_mode="transcription"), word(), False),
    "question_sound":         (session(show_mode="sound"), word(sounds=SOUNDS), False),
    "answer_hebrew":       (session(show_answer=True, word_processed=True), word(), True),
    "pick_mode":           (pick_session(), word(), False),
    "pick_after_answer":   (session(show_answer=True, word_processed=True,
                                    pick_mode_active=True,
                                    last_wrong_distractor_id="w2",
                                    pick_answer_result="wrong"), word(), True),
    "answer_skipped":      (session(show_answer=True, word_processed=True),
                            word(user_word_data={"score": 0, "check_interval": 0,
                                                 "next_check_date": "", "is_skipped": True}), True),

    # края, на которых ломается вёрстка
    "counters_one":        (session(correct_count=1, incorrect_count=1,
                                    result_history=["know", "dont_know"],
                                    total_words_processed=2), word(), False),
    "counters_eleven":     (session(correct_count=11, incorrect_count=11,
                                    result_history=["know"] * 22,
                                    total_words_processed=22), word(), False),
    "long_text":           (session(show_answer=True, word_processed=True),
                            word(word_foreign="הִתְחַשְׁבְנוּת",
                                 translation="взаимный расчёт, сведение счетов, "
                                             "выяснение отношений между сторонами "
                                             "после долгого спора",
                                 transcription="hitχaʃbeˈnut"), True),
    "markup_chars":        (session(show_answer=True, word_processed=True),
                            word(translation="меньше < больше > и & амперсанд",
                                 tones="", references=""), True),
    "no_extras":           (session(show_answer=True, word_processed=True),
                            word(tones="", references=""), True),
}


def main():
    os.makedirs(OUT, exist_ok=True)
    for name, (sess, wd, show_answer) in CASES.items():
        card = build_card(sess, wd, show_answer=show_answer)
        path = os.path.join(OUT, f"{name}.json")
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(card, fh, ensure_ascii=False, indent=1)
        n_extra = len(card.get("extra_content") or [])
        n_btn = len(card.get("buttons") or [])
        pick = "пик" if card.get("pick_options") else "—"
        print(f"  {name:20} кнопок {n_btn}  доп. блоков {n_extra}  {pick}")
    print(f"\nфикстур: {len(CASES)} → {os.path.relpath(OUT, ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
