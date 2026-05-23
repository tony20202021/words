"""Unit tests for card → Telegram HTML renderer."""

import pytest
from app.bot.renderer import render_card_text, _render_footer
from tests.conftest import make_card


class TestRenderCardText:
    def test_foreign_rendered_as_code(self):
        card = make_card(show_answer=False)
        text = render_card_text(card)
        assert "<code>hello</code>" in text

    def test_translation_rendered_plain(self):
        card = make_card(show_answer=True)
        text = render_card_text(card)
        assert "привет" in text

    def test_transcription_rendered_italic(self):
        card = make_card(show_answer=True)
        text = render_card_text(card)
        assert "<i>[hɛˈloʊ]</i>" in text

    def test_label_rendered_bold(self):
        card = make_card(show_answer=False)
        text = render_card_text(card)
        assert "<b>" in text

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
        card = {"content": [], "meta": {}}
        text = render_card_text(card)
        assert isinstance(text, str)

    def test_footer_contains_word_number(self):
        card = make_card(word_number=42)
        text = render_card_text(card)
        assert "42" in text

    def test_footer_contains_counters(self):
        card = make_card(correct=3, incorrect=2)
        # session_pos = 3+2+1 = 6, done = 5
        text = render_card_text(card)
        assert "✓3" in text
        assert "✗2" in text

    def test_no_footer_for_zero_progress(self):
        card = {"content": [], "meta": {"word_number": None, "score_badge": {}, "session_pos": 1,
                                         "correct_count": 0, "incorrect_count": 0}}
        footer = _render_footer(card["meta"])
        assert footer == ""

    def test_unknown_item_type_skipped(self):
        card = {"content": [{"type": "unknown_type", "text": "x"}], "meta": {}}
        text = render_card_text(card)
        assert "x" not in text


class TestRenderFooter:
    def test_score_badge_included(self):
        meta = {
            "word_number": 5,
            "score_badge": {"text": "✓ знал · 7д", "variant": "success", "next_date": "2026-05-27"},
            "session_pos": 4,
            "correct_count": 3,
            "incorrect_count": 0,
        }
        footer = _render_footer(meta)
        assert "5" in footer
        assert "✓ знал · 7д" in footer
        assert "✓3" in footer
