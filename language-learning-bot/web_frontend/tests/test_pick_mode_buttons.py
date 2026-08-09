"""
Пик-режим: кнопки под вариантами приходят из карточки, а не зашиты в шаблон.

Раньше «❓ Не знаю» была написана прямо в шаблоне, а весь card.buttons в
пик-режиме не рендерился вовсе — блок кнопок закрыт условием
{% if not card.pick_options or card.show_answer %}. Вместе с массивом пропадала
кнопка «Пропускать»: настройка show_skip_button в пик-режиме молча не работала,
и снять пометку «пропущено» было нечем.
"""

import re

import pytest
from jinja2 import Environment, FileSystemLoader

TEMPLATES = "app/templates"


@pytest.fixture(scope="module")
def render():
    env = Environment(loader=FileSystemLoader(TEMPLATES))
    tpl = env.get_template("partials/word_card.html")

    def _render(buttons):
        card = {
            "meta": {"score_badge": {"variant": "secondary", "text": "новое"},
                     "word_number": 7, "result_history": [],
                     "correct_count": 0, "incorrect_count": 0, "words_for_today": 5},
            "content": [], "sounds": [], "show_answer": False, "buttons": buttons,
            "pick_options": {"target_modality": "translation", "options": [
                {"word_id": "w1", "target_text": "книга"},
                {"word_id": "w2", "target_text": "лошадь"}]},
        }
        return tpl.render(card=card, lang={"name_ru": "Иврит"}, language_id="l1")

    return _render


def _labels(html):
    return [t.strip() for t in re.findall(r"<button[^>]*>\s*([^<]+?)\s*</button>", html)]


DONT_KNOW = {"id": "pick_dont_know", "text": "❓ Не знаю", "style": "outline-secondary"}
SKIP = {"id": "toggle_skip", "text": "⏩ Пропускать", "style": "outline-secondary"}


def test_skip_button_appears_in_pick_mode(render):
    labels = _labels(render([DONT_KNOW, SKIP]))
    assert "⏩ Пропускать" in labels, labels
    assert "❓ Не знаю" in labels


def test_skip_button_obeys_the_setting(render):
    labels = _labels(render([DONT_KNOW]))
    assert "⏩ Пропускать" not in labels, labels
    assert "❓ Не знаю" in labels


def test_dont_know_text_comes_from_the_card(render):
    """Текст не зашит: сменив его в card_builder, мы меняем все клиенты разом."""
    labels = _labels(render([{**DONT_KNOW, "text": "❓ Понятия не имею"}]))
    assert "❓ Понятия не имею" in labels
    assert "❓ Не знаю" not in labels


def test_dont_know_posts_a_pick_answer_not_show_answer(render):
    """
    Это pick_answer с dont_know: незнание засчитывается и показывается баннер
    результата. show_answer ничего не записывает — перепутав, потеряли бы оценку.
    """
    html = render([DONT_KNOW])
    block = html[html.index("Выберите правильный вариант"):]
    block = block[:block.index("</div>", block.index("Не знаю"))]
    assert "/study/l1/pick_answer" in block
    assert "dont_know" in block


def test_skip_button_posts_toggle_skip(render):
    html = render([DONT_KNOW, SKIP])
    assert "/study/l1/toggle_skip" in html
