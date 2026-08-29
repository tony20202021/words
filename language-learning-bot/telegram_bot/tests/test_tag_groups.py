"""Группа тега в Telegram: таблиц нет, колонки складываются в строку."""
from app.bot.renderer import _tag_group_text, render_extra_texts

ROWS = [
    {"rank": 40, "ru": "один", "ipa": "ʔeˈχad", "foreign": "אֶחָד", "self": False},
    {"rank": 417, "ru": "три", "ipa": "ʃaˈloʃ", "foreign": "שָׁלוֹשׁ", "self": True},
]


def test_line_carries_all_four_columns():
    out = _tag_group_text({"rows": ROWS})
    first = out.split("\n")[0]
    assert "40" in first and "один" in first and "[ʔeˈχad]" in first and "אֶחָד" in first
    # Номер без «#» — как в таблицах остальных клиентов.
    assert "#" not in first


def test_the_word_comes_before_its_transcription():
    first = _tag_group_text({"rows": ROWS}).split("\n")[0]
    assert first.index("אֶחָד") < first.index("[ʔeˈχad]")


def test_the_current_word_is_bold():
    out = _tag_group_text({"rows": ROWS})
    assert "<b>417  три" in out


def test_markup_characters_are_escaped():
    """Символ < в переводе ломает разбор HTML — Telegram не покажет сообщение."""
    out = _tag_group_text({"rows": [{"rank": 1, "ru": "меньше < чем", "ipa": "a & b",
                                     "foreign": "x", "self": False}]})
    assert "&lt;" in out and "&amp;" in out
    assert "меньше < чем" not in out


def test_block_reaches_the_message_list():
    """
    Без своего рендерера блок молча исчезал бы: неизвестный тип пишется в лог,
    но пользователь всё равно ничего не увидит.
    """
    card = {"extra_content": [
        {"type": "label", "text": "🔢 Числительные", "group": "tags"},
        {"type": "tag_group", "group": "tags", "rows": ROWS},
    ]}
    msgs = render_extra_texts(card)
    assert msgs and "Числительные" in msgs[0]
    assert "один" in msgs[0]
