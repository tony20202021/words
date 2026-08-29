"""Группа тега в вебе: четыре колонки и подсветка своей строки.

Блок отличается от огласовок и однокоренных: там две колонки, здесь четыре —
номер в частотном словаре, перевод, транскрипция, слово. Поэтому у него свой
тип, и двухколоночный разбор его не касается.
"""
import pytest

from app.templating import templates

ROWS = [
    {"rank": 40, "ru": "один", "ipa": "ʔeˈχad", "foreign": "אֶחָד", "self": False},
    {"rank": 417, "ru": "три", "ipa": "ʃaˈloʃ", "foreign": "שָׁלוֹשׁ", "self": True},
    {"rank": 890, "ru": "десять", "ipa": "ˈʔeseʁ", "foreign": "עֶשֶׂר", "self": False},
]


@pytest.fixture(scope="module")
def rendered():
    # Через НАСТОЯЩЕЕ окружение приложения: своё не знает про фильтры, и шаблон
    # мог бы сломаться у пользователя при зелёных тестах.
    tpl = templates.env.get_template("partials/word_card.html")
    card = {
        "meta": {"score_badge": {"variant": "secondary", "text": "новое"},
                 "word_number": 417, "result_history": [], "correct_count": 0,
                 "incorrect_count": 0, "words_for_today": 5},
        "content": [], "sounds": [], "buttons": [], "show_answer": True,
        "extra_groups": [{"items": [
            {"type": "label", "text": "🔢 Числительные", "group": "tags"},
            {"type": "tag_group", "group": "tags", "tag": "числительные", "rows": ROWS},
        ]}],
    }
    return tpl.render(card=card, lang={"name_ru": "Иврит"}, language_id="l1")


def test_all_four_columns_are_present(rendered):
    assert "#40" in rendered and "#890" in rendered      # номер в словаре
    assert "один" in rendered and "десять" in rendered   # перевод
    assert "[ʔeˈχad]" in rendered                        # транскрипция
    assert "אֶחָד" in rendered                            # слово


def test_the_current_word_is_highlighted(rendered):
    # Иначе своё слово в списке из двадцати одного числительного не найти.
    assert "table-warning" in rendered


def test_hebrew_column_is_right_to_left(rendered):
    assert 'dir="rtl"' in rendered


def test_rows_keep_the_given_order(rendered):
    # Порядок задаётся в определениях тегов вручную: частотный список к нему
    # безразличен, «один» стоит 40-м, «десять» 890-м.
    assert rendered.index("один") < rendered.index("три") < rendered.index("десять")
