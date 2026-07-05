"""Unit tests for card → InlineKeyboardMarkup builder."""

import pytest
from app.bot.keyboards import build_card_keyboard, build_language_keyboard, _callback
from tests.conftest import make_card


def all_buttons(keyboard):
    return [b for row in keyboard.inline_keyboard for b in row]


def callbacks(keyboard):
    return [b.callback_data for b in all_buttons(keyboard)]


def texts(keyboard):
    return [b.text for b in all_buttons(keyboard)]


class TestBuildCardKeyboard:
    def test_before_answer_has_know_and_show_answer(self):
        card = make_card(show_answer=False)
        kb = build_card_keyboard(card, "lang1")
        cbs = callbacks(kb)
        assert "study:lang1:know" in cbs
        assert "study:lang1:show_answer" in cbs

    def test_before_answer_has_toggle_skip(self):
        card = make_card(show_answer=False)
        kb = build_card_keyboard(card, "lang1")
        assert "study:lang1:toggle_skip" in callbacks(kb)

    def test_after_answer_has_rate_button(self):
        card = make_card(show_answer=True)
        kb = build_card_keyboard(card, "lang1")
        cbs = callbacks(kb)
        assert any("rate" in c for c in cbs)

    def test_rate_dont_know_when_not_score_changed(self):
        card = make_card(show_answer=True, score_changed=False)
        kb = build_card_keyboard(card, "lang1")
        assert "study:lang1:rate:dont_know" in callbacks(kb)

    def test_rate_know_when_score_changed(self):
        card = make_card(show_answer=True, score_changed=True)
        kb = build_card_keyboard(card, "lang1")
        assert "study:lang1:rate:know" in callbacks(kb)

    def test_after_answer_no_know_or_show_answer(self):
        card = make_card(show_answer=True)
        kb = build_card_keyboard(card, "lang1")
        cbs = callbacks(kb)
        assert "study:lang1:know" not in cbs
        assert "study:lang1:show_answer" not in cbs

    def test_language_id_embedded_in_callbacks(self):
        card = make_card(show_answer=False)
        kb = build_card_keyboard(card, "my-lang-id")
        for cb in callbacks(kb):
            assert "my-lang-id" in cb

    def test_button_texts_come_from_card(self):
        card = make_card(show_answer=False)
        kb = build_card_keyboard(card, "lang1")
        txts = texts(kb)
        assert "✅ Знаю" in txts
        assert "❓ Не знаю" in txts

    def test_empty_buttons_list(self):
        card = {"buttons": [], "meta": {}}
        kb = build_card_keyboard(card, "lang1")
        assert all_buttons(kb) == []


    def test_sound_buttons_added_when_sounds_present(self):
        card = make_card(show_answer=False)
        card["sounds"] = ["chinese/word1.mp3"]
        kb = build_card_keyboard(card, "lang1")
        cbs = callbacks(kb)
        assert "study:lang1:sound:0" in cbs

    def test_no_sound_buttons_when_no_sounds(self):
        card = make_card(show_answer=False)
        card["sounds"] = []
        kb = build_card_keyboard(card, "lang1")
        cbs = callbacks(kb)
        assert not any("sound" in c for c in cbs)

    def test_single_sound_not_numbered(self):
        card = make_card(show_answer=False)
        card["sounds"] = ["a.mp3"]
        kb = build_card_keyboard(card, "lang1")
        txts = texts(kb)
        assert "🔊" in txts
        assert "🔊 1" not in txts

    def test_multiple_sounds_numbered(self):
        card = make_card(show_answer=False)
        card["sounds"] = ["a.mp3", "b.mp3"]
        kb = build_card_keyboard(card, "lang1")
        txts = texts(kb)
        assert "🔊 1" in txts
        assert "🔊 2" in txts
        cbs = callbacks(kb)
        assert "study:lang1:sound:0" in cbs
        assert "study:lang1:sound:1" in cbs


class TestPickModeKeyboard:
    def _pick_card(self, show_answer=False, modality="translation"):
        card = {
            "show_answer": show_answer,
            "pick_options": {
                "target_modality": modality,
                "options": [
                    {"word_id": "w1", "target_text": "привет", "is_correct": True},
                    {"word_id": "w2", "target_text": "мир", "is_correct": False},
                    {"word_id": "w3", "target_text": "кот", "is_correct": False},
                ],
            },
            "buttons": [{"id": "know", "text": "✅ Знаю", "style": "success"}],
            "meta": {},
        }
        return card

    def test_pick_mode_shows_option_texts(self):
        card = self._pick_card()
        kb = build_card_keyboard(card, "lang1")
        txts = texts(kb)
        assert "привет" in txts
        assert "мир" in txts

    def test_pick_mode_callbacks_contain_word_ids(self):
        card = self._pick_card()
        kb = build_card_keyboard(card, "lang1")
        cbs = callbacks(kb)
        assert "study:lang1:pick_answer:w1" in cbs
        assert "study:lang1:pick_answer:w2" in cbs

    def test_pick_mode_has_dont_know_button(self):
        card = self._pick_card()
        kb = build_card_keyboard(card, "lang1")
        cbs = callbacks(kb)
        assert "study:lang1:pick_answer:dont_know" in cbs

    def test_pick_mode_hides_normal_buttons(self):
        card = self._pick_card()
        kb = build_card_keyboard(card, "lang1")
        cbs = callbacks(kb)
        assert "study:lang1:know" not in cbs
        assert "study:lang1:show_answer" not in cbs

    def test_pick_mode_sound_modality_shows_numbered_buttons(self):
        card = self._pick_card(modality="sound")
        kb = build_card_keyboard(card, "lang1")
        txts = texts(kb)
        assert "▶ 1" in txts
        assert "Выбрать 1" in txts

    def test_pick_mode_inactive_after_answer(self):
        card = self._pick_card(show_answer=True)
        kb = build_card_keyboard(card, "lang1")
        cbs = callbacks(kb)
        # After answer, normal buttons shown even if pick_options is present
        assert "study:lang1:know" in cbs or any("rate" in c for c in cbs)

    def test_ban_distractor_button_shown(self):
        card = make_card(show_answer=True)
        card["last_wrong_distractor_id"] = "bad-word-id"
        kb = build_card_keyboard(card, "lang1")
        cbs = callbacks(kb)
        assert "study:lang1:add_forbidden_pair:bad-word-id" in cbs

    def test_ban_distractor_button_absent_without_id(self):
        card = make_card(show_answer=True)
        card["last_wrong_distractor_id"] = None
        kb = build_card_keyboard(card, "lang1")
        cbs = callbacks(kb)
        assert not any("add_forbidden_pair" in c for c in cbs)


class TestBuildLanguageKeyboard:
    def test_one_button_per_language(self):
        langs = [
            {"id": "l1", "name_ru": "Английский", "name_foreign": "English"},
            {"id": "l2", "name_ru": "Китайский", "name_foreign": "中文"},
        ]
        kb = build_language_keyboard(langs)
        btns = all_buttons(kb)
        assert len(btns) == 2
        assert btns[0].callback_data == "lang:l1"
        assert btns[1].callback_data == "lang:l2"

    def test_label_includes_foreign_name(self):
        langs = [{"id": "l1", "name_ru": "Английский", "name_foreign": "English"}]
        kb = build_language_keyboard(langs)
        assert "English" in all_buttons(kb)[0].text

    def test_label_without_foreign_name(self):
        langs = [{"id": "l1", "name_ru": "Английский", "name_foreign": ""}]
        kb = build_language_keyboard(langs)
        assert all_buttons(kb)[0].text == "Английский"


class TestCallback:
    def test_rate_includes_rating(self):
        cb = _callback({"id": "rate", "rating": "know"}, "lang1")
        assert cb == "study:lang1:rate:know"

    def test_know_callback(self):
        assert _callback({"id": "know"}, "lang1") == "study:lang1:know"

    def test_show_answer_callback(self):
        assert _callback({"id": "show_answer"}, "lang1") == "study:lang1:show_answer"

    def test_toggle_skip_callback(self):
        assert _callback({"id": "toggle_skip"}, "lang1") == "study:lang1:toggle_skip"
