"""
Блок дополнительной информации: таблица, а не строка текста.

Строки вида «[#28] אוֹתְךָ [ʔotˈχa] тебя» начинаются с ивритской буквы. Пока это
была одна строка текста, любой рендерер брал направление абзаца по первому
сильному символу и уводил ВСЮ строку вправо — вместе с русским хвостом. Задать
направление абзацу оказалось мало: иврит и русский всё равно шли одной строкой,
и колонки не выстраивались.

Теперь сервер отдаёт разобранные строки, а клиент рисует таблицу: у иврита своя
колонка (справа налево, прижата вправо), у русского своя (слева направо, прижата
влево). Выравнивание стало свойством вёрстки, а не догадкой о направлении.
"""

import re
from pathlib import Path

import pytest
from jinja2 import Environment, FileSystemLoader

TEMPLATES = "app/templates"

ROWS = [
    {"marker": "[#28]", "foreign": "אוֹתְךָ [ʔotˈχa]", "ru": "тебя"},
    {"marker": "[#33]", "foreign": "אוֹתִי [ʔoˈti]", "ru": "меня"},
]


@pytest.fixture(scope="module")
def render():
    env = Environment(loader=FileSystemLoader(TEMPLATES))
    tpl = env.get_template("partials/word_card.html")

    def _render(extra_item):
        card = {
            "meta": {"score_badge": {"variant": "secondary", "text": "новое"},
                     "word_number": 7, "result_history": [], "correct_count": 0,
                     "incorrect_count": 0, "words_for_today": 5},
            "content": [], "sounds": [], "buttons": [], "show_answer": True,
            "extra_groups": [{"items": [extra_item]}],
        }
        return tpl.render(card=card, lang={"name_ru": "Иврит"}, language_id="l1")

    return _render


HEADER = {"header": "<b>את</b>: <i>слов: 2</i>",
          "header_foreign": "<b>את</b>", "header_ru": "слов: 2"}


def test_rows_are_rendered_as_a_table(render):
    html = render({"type": "extra", "group": "references", "text": "старый текст",
                   **HEADER, "rows": ROWS})
    assert "<table" in html
    assert html.count("<tr>") == 3, "две строки данных плюс заголовочная"
    assert "אוֹתְךָ" in html and "тебя" in html
    # Старый текст одной строкой больше не рисуется — иначе блок задвоился бы.
    assert "старый текст" not in html


def test_table_has_cell_borders(render):
    html = render({"type": "extra", "group": "references", "text": "", **HEADER, "rows": ROWS})
    m = re.search(r"<table[^>]*>", html)
    assert m and "table-bordered" in m.group(0), m.group(0) if m else html[:200]
    assert "table-borderless" not in html


def test_header_is_split_into_the_same_two_cells(render):
    """
    Заголовок тоже двуязычный и отдельной строкой уезжал вправо по первой
    ивритской букве — ровно как строки данных до таблицы.
    """
    html = render({"type": "extra", "group": "references", "text": "", **HEADER, "rows": ROWS})
    head = html[html.index("<thead"):html.index("</thead>")]
    assert 'dir="rtl"' in head and 'dir="ltr"' in head, head
    assert "את" in head and "слов: 2" in head


def test_foreign_column_is_enlarged(render):
    """Огласовка — мелкие знаки под буквами, в общем кегле её не разглядеть."""
    html = render({"type": "extra", "group": "references", "text": "", **HEADER, "rows": ROWS})
    cells = [c for c in re.findall(r"<td[^>]*>", html) if 'dir="rtl"' in c]
    assert cells and all("word-extra-foreign" in c for c in cells), cells

    base = (Path(__file__).resolve().parents[1] / "app" / "templates" / "base.html").read_text(encoding="utf-8")
    m = re.search(r"\.word-extra-foreign\s*\{([^}]*)\}", base)
    assert m, "класс объявлен, но стиля для него нет"
    assert "font-size" in m.group(1), m.group(1)


def test_hebrew_column_is_right_to_left_and_russian_is_not(render):
    html = render({"type": "extra", "group": "references", "text": "",
                   "header": "", "rows": ROWS})
    cells = re.findall(r"<td[^>]*>", html)
    rtl = [c for c in cells if 'dir="rtl"' in c]
    ltr = [c for c in cells if 'dir="ltr"' in c]
    assert len(rtl) == 2, cells
    assert len(ltr) == 2, cells
    assert all("text-end" in c for c in rtl), rtl
    assert all("text-start" in c for c in ltr), ltr


def test_table_itself_runs_left_to_right(render):
    """Ряды должны идти слева направо, иначе колонки поменяются местами."""
    html = render({"type": "extra", "group": "references", "text": "",
                   "header": "", "rows": ROWS})
    m = re.search(r"<table[^>]*>", html)
    assert m and 'dir="ltr"' in m.group(0), m.group(0) if m else html[:200]


def test_block_without_rows_falls_back_to_text(render):
    """
    Радикалы и офлайн-партии, скачанные до этой версии, разобранных строк не
    имеют — они обязаны продолжать рисоваться, а не исчезнуть.
    """
    html = render({"type": "extra", "group": "radicals", "text": "水 — вода"})
    assert "水 — вода" in html
    assert "<table" not in html
