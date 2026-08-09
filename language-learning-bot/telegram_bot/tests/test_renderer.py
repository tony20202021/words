"""Unit tests for card → Telegram HTML renderer."""

import pytest
from app.bot.renderer import render_card_text, render_extra_texts, _render_footer
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
        meta = {"word_number": None, "score_badge": {}, "session_pos": 1,
                "correct_count": 0, "incorrect_count": 0}
        footer = _render_footer(meta)
        assert footer == ""

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
    def test_footer_always_empty(self):
        meta = {
            "word_number": 5,
            "score_badge": {"text": "✓ знал · 7д", "variant": "success", "next_date": "2026-05-27"},
            "session_pos": 4,
            "correct_count": 3,
            "incorrect_count": 0,
        }
        footer = _render_footer(meta)
        assert footer == ""


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

