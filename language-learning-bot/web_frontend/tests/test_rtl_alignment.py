"""
Блок дополнительной информации: направление строки.

Строки вида «[#28] אוֹתְךָ [ʔotˈχa] тебя» начинаются с ивритской буквы. Браузер
берёт направление абзаца по первому сильному символу, поэтому ВСЯ строка
прижималась вправо — вместе с русским хвостом, и читать список однокоренных было
неудобно. Ивритские слова внутри при этом должны оставаться справа налево:
направление задаётся блоку, а не отменяется у слов.
"""

import re
from pathlib import Path

import pytest

TEMPLATE = (Path(__file__).resolve().parents[1]
            / "app" / "templates" / "partials" / "word_card.html")


@pytest.fixture(scope="module")
def html() -> str:
    return TEMPLATE.read_text(encoding="utf-8")


def test_extra_block_sets_left_to_right_direction(html):
    line = next(l for l in html.split("\n") if "item.text | safe" in l)
    assert 'dir="ltr"' in line, line


def test_direction_is_set_on_the_block_not_on_words(html):
    """
    Ивритские слова обязаны остаться RTL. Попытка «починить» это, перевернув
    сами слова, сломала бы их чтение.
    """
    assert "unicode-bidi" not in html
    assert 'dir="rtl"' not in html
