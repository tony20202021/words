"""Unit tests for card → Telegram HTML renderer."""

import pytest
from app.bot.renderer import render_card_text, render_extra_texts, forbidden_pairs_count
from tests.conftest import make_card


class TestRenderCardText:
    def test_foreign_rendered_bold(self):
        card = make_card(show_answer=False)
        text = render_card_text(card)
        assert "<b>hello</b>" in text

    def test_translation_rendered_bold(self):
        card = make_card(show_answer=True)
        text = render_card_text(card)
        assert "<b>привет</b>" in text

    def test_transcription_rendered_bold(self):
        card = make_card(show_answer=True)
        text = render_card_text(card)
        assert "<b>[hɛˈloʊ]</b>" in text

    def test_label_rendered_plain(self):
        card = make_card(show_answer=False)
        text = render_card_text(card)
        # labels are plain text with newline, NOT wrapped in <b>
        assert "<b>📝 Слово на иностранном:</b>" not in text
        assert "📝 Слово на иностранном:" in text

    def test_notice_rendered_as_plain(self):
        card = make_card(show_answer=False)
        card["content"].insert(0, {"type": "notice", "variant": "success", "text": "✅ Интервал: 7 дн."})
        text = render_card_text(card)
        assert "✅ Интервал: 7 дн." in text

    def test_hint_rendered_italic(self):
        card = make_card(show_answer=False)
        card["content"].append({"type": "hint", "text": "💡 some hint"})
        text = render_card_text(card)
        assert "<i>💡 some hint</i>" in text

    def test_empty_card_no_crash(self):
        card = {"content": [], "extra_content": [], "meta": {}}
        text = render_card_text(card)
        assert isinstance(text, str)

    def test_header_contains_word_number(self):
        card = make_card(word_number=42)
        text = render_card_text(card)
        assert "42" in text

    def test_header_contains_counters(self):
        card = make_card(correct=3, incorrect=2)
        text = render_card_text(card)
        assert "3" in text
        assert "2" in text

    def test_no_footer_for_zero_progress(self):
        # Футера у карточки нет: текст заканчивается последним элементом content
        card = make_card(show_answer=False, correct=0, incorrect=0)
        text = render_card_text(card)
        assert text.endswith("<b>hello</b>")

    def test_unknown_item_type_skipped(self):
        card = {"content": [{"type": "unknown_type", "text": "x"}], "extra_content": [], "meta": {}}
        text = render_card_text(card)
        assert "x" not in text

    def test_extra_content_excluded_from_main_card(self):
        card = make_card(show_answer=True)
        card["extra_content"] = [
            {"type": "label", "text": "🎵 Тоны:", "group": "tones"},
            {"type": "extra", "text": "1声 2声 3声", "group": "tones"},
        ]
        text = render_card_text(card)
        assert "1声 2声 3声" not in text
        assert "🎵 Тоны:" not in text

    def test_extra_absent_no_extra_leaked(self):
        card = make_card(show_answer=True)
        card["extra_content"] = []
        text = render_card_text(card)
        assert "──────────" not in text


class TestRenderFooter:
    def test_no_footer_with_progress(self):
        # Даже когда в meta есть прогресс и бейдж, подписи внизу карточки нет
        card = make_card(show_answer=True, word_number=5, correct=3, incorrect=0)
        text = render_card_text(card)
        assert text.endswith("<b>hello</b>")


class TestRenderExtraTexts:
    def test_empty_extra_returns_empty_list(self):
        card = make_card(show_answer=True)
        assert render_extra_texts(card) == []

    def test_one_group_one_message(self):
        card = make_card(show_answer=True)
        card["extra_content"] = [
            {"type": "label", "text": "🎵 Тоны:", "group": "tones"},
            {"type": "extra", "text": "1声 2声", "group": "tones"},
        ]
        msgs = render_extra_texts(card)
        assert len(msgs) == 1
        assert "🎵 Тоны:" in msgs[0]
        assert "1声 2声" in msgs[0]

    def test_two_groups_two_messages(self):
        card = make_card(show_answer=True)
        card["extra_content"] = [
            {"type": "label", "text": "🎵 Тоны:", "group": "tones"},
            {"type": "extra", "text": "tones content", "group": "tones"},
            {"type": "label", "text": "🔍 Ссылки:", "group": "references"},
            {"type": "extra", "text": "refs content", "group": "references"},
        ]
        msgs = render_extra_texts(card)
        assert len(msgs) == 2
        assert "Тоны:" in msgs[0]
        assert "Ссылки:" in msgs[1]

    def test_three_groups_three_messages(self):
        card = make_card(show_answer=True)
        card["extra_content"] = [
            {"type": "label", "text": "🎵 Тоны:", "group": "tones"},
            {"type": "extra", "text": "t", "group": "tones"},
            {"type": "label", "text": "🔍 Ссылки:", "group": "references"},
            {"type": "extra", "text": "r", "group": "references"},
            {"type": "label", "text": "🔍 Радикалы:", "group": "radicals"},
            {"type": "extra", "text": "rad", "group": "radicals"},
        ]
        msgs = render_extra_texts(card)
        assert len(msgs) == 3

    def test_long_content_split(self):
        card = make_card(show_answer=True)
        big_text = "x" * 4500
        card["extra_content"] = [
            {"type": "label", "text": "🔍 Ссылки:", "group": "references"},
            {"type": "extra", "text": big_text, "group": "references"},
        ]
        msgs = render_extra_texts(card)
        assert len(msgs) >= 2
        assert all(len(m) <= 4000 for m in msgs)

    def test_group_field_ignored_in_rendering(self):
        card = make_card(show_answer=True)
        card["extra_content"] = [
            {"type": "label", "text": "Радикалы:", "group": "radicals"},
            {"type": "extra", "text": "木", "group": "radicals"},
        ]
        msgs = render_extra_texts(card)
        assert len(msgs) == 1
        assert "木" in msgs[0]

    def test_no_extra_content_key(self):
        card = {"content": [], "meta": {}}
        assert render_extra_texts(card) == []

# ── экранирование ────────────────────────────────────────────────────────────

def test_text_from_the_database_is_escaped():
    """
    Сообщение уходит с parse_mode="HTML", а перевод и подсказки приходят из БД.
    Символ < или & ломал разбор — Telegram отвечал ошибкой, и карточка не
    показывалась вовсе.
    """
    from app.bot.renderer import render_card_text

    card = {
        "meta": {},
        "content": [
            {"type": "foreign", "text": "a < b"},
            {"type": "translation", "text": "Смит & сын"},
            {"type": "hint", "text": "<script>alert(1)</script>"},
        ],
    }
    out = render_card_text(card)
    assert "a &lt; b" in out
    assert "Смит &amp; сын" in out
    assert "<script>" not in out
    assert "&lt;script&gt;" in out
    # Разметка, которую добавляет сам рендер, остаётся рабочей.
    assert "<b>a &lt; b</b>" in out


def test_prepared_markup_of_extra_blocks_is_not_escaped():
    """
    Варианты огласовки и однокоренные card_builder отдаёт уже с <b>/<i> — это его
    разметка, а не пользовательский ввод, и экранировать её значило бы показать
    учащемуся угловые скобки.
    """
    from app.bot.renderer import render_card_text

    card = {"meta": {}, "content": [{"type": "extra", "text": "<b>עם</b>: <i>2</i>"}]}
    assert "<b>עם</b>: <i>2</i>" in render_card_text(card)



# ── forbidden_quiz_pairs ─────────────────────────────────────────────────────
# card_builder кладёт в extra_content блок с забаненными комбинациями, а рендер
# его не знал и молча выбрасывал: пользователь Telegram не видел накопившихся
# запретов и не мог их снять (кнопка была только в вебе).

class TestForbiddenQuizPairs:
    @staticmethod
    def _card_with_forbidden(word_ids):
        card = make_card(show_answer=True)
        card["extra_content"] = [
            {"type": "forbidden_quiz_pairs", "word_ids": word_ids,
             "group": "forbidden_quiz_pairs"},
        ]
        return card

    def test_forbidden_block_is_rendered(self):
        msgs = render_extra_texts(self._card_with_forbidden(["w2", "w3"]))
        assert len(msgs) == 1
        assert "2" in msgs[0]
        assert "апрещ" in msgs[0]

    def test_forbidden_block_is_its_own_message(self):
        card = make_card(show_answer=True)
        card["extra_content"] = [
            {"type": "label", "text": "🎵 Тоны:", "group": "tones"},
            {"type": "extra", "text": "1声 2声", "group": "tones"},
            {"type": "forbidden_quiz_pairs", "word_ids": ["w2"],
             "group": "forbidden_quiz_pairs"},
        ]
        msgs = render_extra_texts(card)
        assert len(msgs) == 2
        assert "Тоны" in msgs[0]
        assert "1声 2声" in msgs[0]
        assert "апрещ" in msgs[1]
        assert "Тоны" not in msgs[1]

    def test_count_helper_reads_word_ids(self):
        assert forbidden_pairs_count(self._card_with_forbidden(["a", "b", "c"])) == 3

    def test_count_helper_zero_without_block(self):
        assert forbidden_pairs_count(make_card(show_answer=True)) == 0

    def test_count_helper_zero_for_empty_list(self):
        assert forbidden_pairs_count(self._card_with_forbidden([])) == 0


def test_unknown_content_type_is_logged(caplog):
    """Молчаливое расхождение с card_builder — это исчезнувший с экрана блок."""
    import logging
    card = {"meta": {}, "content": [{"type": "brand_new_type", "text": "x"}]}
    with caplog.at_level(logging.WARNING, logger="app.bot.renderer"):
        render_card_text(card)
    assert any("brand_new_type" in r.getMessage() for r in caplog.records)

def test_extra_lines_get_left_to_right_direction():
    """
    В Telegram нельзя задать направление абзаца, а строка вида
    «[#28] אוֹתְךָ [ʔotˈχa] тебя» начинается с ивритской буквы — клиент прижимал
    её вправо вместе с русским хвостом. Направление задаёт метка LRM в начале
    строки; сам текст не меняется.
    """
    from app.bot.renderer import render_extra_texts

    card = {"extra_content": [
        {"type": "label", "text": "🌱 Слова с той же основой:", "group": "references"},
        {"type": "extra", "text": "<b>את</b>: <i>слов: 2</i>\n<i>[#28]</i>אוֹתְךָ тебя",
         "group": "references"},
    ]}
    body = "\n".join(render_extra_texts(card))
    content = [l for l in body.split("\n") if "את" in l or "אוֹתְךָ" in l]
    assert content, body
    for line in content:
        assert line.startswith("\u200e"), repr(line)
    # Текст не тронут — метка только в начале.
    assert "אוֹתְךָ тебя" in body
    # Подпись блока — обычный русский текст, метка ей не нужна.
    assert "🌱 Слова с той же основой:" in body

def test_extra_block_uses_the_parsed_rows():
    """
    Таблиц в Telegram нет, но колонки уже разобраны сервером — из них собирается
    ровная строка, а не сырой текст блока.

    Порядок колонок тот же, что у группы тега: номер, перевод, слово,
    транскрипция. Прежде строка шла как «слово [транскрипция] — перевод», и две
    таблицы на одной карточке читались по-разному.
    """
    from app.bot.renderer import render_extra_texts

    card = {"extra_content": [
        {"type": "label", "text": "🌱 Слова с той же основой:", "group": "references"},
        {"type": "extra", "text": "СЫРОЙ ТЕКСТ", "group": "references",
         "header": "<b>את</b>: <i>слов: 2</i>",
         "rows": [{"marker": "[#28]", "rank": 28, "foreign": "אוֹתְךָ",
                   "ipa": "ʔotˈχa", "ru": "тебя"}]},
    ]}
    body = "\n".join(render_extra_texts(card))
    assert "28  тебя  אוֹתְךָ  [ʔotˈχa]" in body, body
    assert "СЫРОЙ ТЕКСТ" not in body


def test_extra_block_without_rows_still_renders():
    """Офлайн-партии, скачанные до этой версии, разобранных строк не имеют."""
    from app.bot.renderer import render_extra_texts

    card = {"extra_content": [
        {"type": "label", "text": "🈶 Радикалы:", "group": "radicals"},
        {"type": "extra", "text": "水 — вода", "group": "radicals"},
    ]}
    assert "水 — вода" in "\n".join(render_extra_texts(card))



# ── примеры для чтения ──────────────────────────────────────────────────────
#
# Новый тип блока. В Telegram у рендереров есть свойство, которое уже один раз
# стоило показа: тип без рендерера проходит через _warn_unknown_type и ИСЧЕЗАЕТ
# с экрана. Так пропадали запрещённые дистракторы — в логе предупреждение, у
# пользователя пусто. Поэтому проверка требует не «не упало», а чтобы текст
# предложений был в сообщении.

БЛОК_ЧТЕНИЯ = {
    "type": "reading", "group": "reading",
    "rows": [
        {"marker": "1", "rank": 1, "foreign": "יש זמן", "ru": ""},
        {"marker": "", "rank": None, "foreign": "", "ru": "Время есть."},
        {"marker": "2", "rank": 2, "foreign": "זמן טוב", "ru": ""},
        {"marker": "", "rank": None, "foreign": "", "ru": "Хорошее время."},
    ],
}


def test_примеры_для_чтения_не_исчезают():
    from app.bot.renderer import render_extra_texts
    тексты = render_extra_texts({"extra_content": [
        {"type": "label", "text": "📖 Примеры для чтения:", "group": "reading"},
        БЛОК_ЧТЕНИЯ,
    ]})
    собрано = "\n".join(тексты)
    assert "יש זמן" in собрано, "предложение пропало из сообщения"
    assert "Время есть." in собрано, "перевод пропал из сообщения"


def test_перевод_идёт_своей_строкой_под_предложением():
    """Тот же порядок, что в приложении и на сайте: текст, под ним перевод."""
    from app.bot.renderer import _reading_text
    строки = _reading_text(БЛОК_ЧТЕНИЯ).split("\n")
    assert len(строки) == 4
    assert строки[0].startswith("1.") and "יש זמן" in строки[0]
    assert строки[1] == "<i>Время есть.</i>"


def test_текст_предложения_экранируется():
    """
    Сообщение уходит с parse_mode=HTML, а предложения — данные. Символ «<» в
    примере ломал бы разбор, и карточка не показалась бы вовсе.
    """
    from app.bot.renderer import _reading_text
    вышло = _reading_text({"rows": [
        {"marker": "1", "foreign": "a < b", "ru": ""},
        {"marker": "", "foreign": "", "ru": "a & b"},
    ]})
    assert "&lt;" in вышло and "&amp;" in вышло
