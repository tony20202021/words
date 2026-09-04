"""Отметка прослушанного варианта в пик-режиме по звуку.

Кнопки «🔊 ▶ 1», «🔊 ▶ 2» неразличимы между собой, звук отзвучал и следа не
оставил. Без отметки после второго-третьего нажатия уже не вспомнить, что
именно играло, и выбирать приходится наугад.
"""
from pathlib import Path

import pytest

from app.templating import templates

JS = Path(__file__).resolve().parents[1] / "app" / "static" / "js" / "word_card.js"


@pytest.fixture(scope="module")
def rendered():
    tpl = templates.env.get_template("partials/word_card.html")
    card = {
        "meta": {"score_badge": {"variant": "secondary", "text": "новое"},
                 "word_number": 7, "result_history": [], "correct_count": 0,
                 "incorrect_count": 0, "words_for_today": 5},
        "content": [], "sounds": [], "buttons": [], "show_answer": False,
        "extra_groups": [],
        "pick_options": {
            "target_modality": "sound",
            "options": [
                {"word_id": "w1", "target_text": "a.mp3|b.mp3", "is_correct": True},
                {"word_id": "w2", "target_text": "c.mp3", "is_correct": False},
            ],
        },
    }
    return tpl.render(card=card, lang={"name_ru": "Иврит"}, language_id="l1")


def test_listen_buttons_are_marked_up_for_highlighting(rendered):
    assert rendered.count("btn-listen") == 2
    assert 'data-opt="1"' in rendered and 'data-opt="2"' in rendered


def test_clicking_listen_calls_the_marker(rendered):
    assert "markListened(this)" in rendered
    # Отметка обязана стоять ДО проигрывания: иначе при ошибке звука вариант
    # останется неотмеченным, хотя человек на него нажал.
    assert rendered.index("markListened(this)") < rendered.index("playSounds([")


def test_the_marker_clears_the_previous_choice():
    js = JS.read_text(encoding="utf-8")
    assert "function markListened" in js
    # Снимаем заливку со всех, потом ставим на нажатую — иначе отметок
    # накопится столько, сколько раз нажали.
    assert "querySelectorAll('.btn-listen')" in js
    assert js.index("querySelectorAll('.btn-listen')") < js.index("btn.classList.add('btn-secondary')")
