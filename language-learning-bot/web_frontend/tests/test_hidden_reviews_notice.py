"""
Веб говорит про повторения, отсечённые настройкой «начальный номер слова».

Разбор 07.11.2026: у живого пользователя порог стоял на 3000, и 2546 слов
ждали повторения ниже него — они не показались бы никогда. Отбор на занятие
фильтрует по этой настройке ВСЕ слова сразу, а не только новые.

Решение владельца: отбор оставить, молчание убрать. Молчание тут и было
дефектом — узнать о потере человеку было неоткуда.
"""
import pytest

from app.templating import templates


class FakeRequest:
    """Базовый шаблон читает только request.session — больше ничего не нужно."""
    session: dict = {}


def render(hidden=0, start_word=1):
    tpl = templates.env.get_template("stats.html")
    stats = {
        "words_studied": 3727, "words_known": 3584, "words_skipped": 0,
        "total_words": 8466, "words_for_today": 299,
        "progress_percentage": 42.3,
        "words_hidden_by_start_word": hidden, "start_word": start_word,
    }
    item = {"language": {"id": "l1", "name_ru": "Английский", "name_foreign": "English"},
            "stats": stats}
    return tpl.render(request=FakeRequest(), stats_list=[item],
                      target_lang_id="l1", chart_sections=[], chart_captions={})


def test_the_page_says_how_many_reviews_the_threshold_hides():
    html = render(hidden=2546, start_word=3000)
    assert "2546" in html
    assert "3000" in html
    assert "повторения" in html


def test_the_page_stays_quiet_when_nothing_is_hidden():
    """
    Опора. Предупреждение, которое висит всегда, перестают читать — и оно не
    сработает тогда, когда понадобится.
    """
    html = render(hidden=0, start_word=1)
    assert "отсечены" not in html
