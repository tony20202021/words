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
            # Что BLS отдаёт на самом деле: до ответа — свои кнопки пик-режима,
            # после — обычные. Раньше здесь всегда стоял know, потому что клиент
            # всё равно выбрасывал buttons[] и рисовал «Не знаю» сам.
            "buttons": (
                [{"id": "know", "text": "✅ Знаю", "style": "success"},
                 {"id": "rate", "rating": "dont_know", "text": "❌ Не знаю", "style": "danger"}]
                if show_answer else
                [{"id": "pick_dont_know", "text": "❓ Не знаю", "style": "outline-secondary"},
                 {"id": "toggle_skip", "text": "⏩ Пропускать", "style": "outline-secondary"}]
            ),
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
        assert "study:lang1:pick:w1" in cbs
        assert "study:lang1:pick:w2" in cbs

    def test_pick_mode_has_dont_know_button(self):
        card = self._pick_card()
        kb = build_card_keyboard(card, "lang1")
        cbs = callbacks(kb)
        assert "study:lang1:pick:dont_know" in cbs

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
        """Кнопка приходит в buttons[] — правило «когда показывать» в card_builder."""
        card = make_card(show_answer=True)
        card["buttons"] = card.get("buttons", []) + [
            {"id": "ban_pair", "text": "🚫 Не показывать такую комбинацию",
             "style": "outline-warning", "bad_word_id": "bad-word-id"}]
        kb = build_card_keyboard(card, "lang1")
        cbs = callbacks(kb)
        assert "study:lang1:ban:bad-word-id" in cbs

    def test_ban_distractor_button_absent_without_id(self):
        card = make_card(show_answer=True)
        card["last_wrong_distractor_id"] = None
        kb = build_card_keyboard(card, "lang1")
        cbs = callbacks(kb)
        assert not any(":ban:" in c for c in cbs)


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


class TestClearForbiddenPairsButton:
    """Запреты на комбинации копились молча: в Telegram не было ни счётчика, ни
    способа их снять, хотя BLS отдаёт блок, а клиентский метод уже написан."""

    @staticmethod
    def _card(word_ids):
        card = make_card(show_answer=True)
        card["extra_content"] = [
            {"type": "forbidden_quiz_pairs", "word_ids": word_ids,
             "group": "forbidden_quiz_pairs"},
        ]
        return card

    def test_button_shown_when_pairs_banned(self):
        kb = build_card_keyboard(self._card(["w2", "w3"]), "lang1")
        assert "study:lang1:clear_pairs" in callbacks(kb)

    def test_button_shows_count(self):
        kb = build_card_keyboard(self._card(["w2", "w3"]), "lang1")
        assert any("(2)" in t for t in texts(kb))

    def test_button_absent_without_pairs(self):
        kb = build_card_keyboard(make_card(show_answer=True), "lang1")
        assert "study:lang1:clear_pairs" not in callbacks(kb)

    def test_button_absent_for_empty_list(self):
        kb = build_card_keyboard(self._card([]), "lang1")
        assert "study:lang1:clear_pairs" not in callbacks(kb)

# ── кнопки пик-режима приходят из карточки ───────────────────────────────────

def _pick_card(buttons):
    return {
        "show_answer": False,
        "buttons": buttons,
        "pick_options": {"target_modality": "translation", "options": [
            {"word_id": "w1", "target_text": "книга"},
            {"word_id": "w2", "target_text": "лошадь"}]},
    }


_DONT_KNOW = {"id": "pick_dont_know", "text": "❓ Не знаю"}
_SKIP = {"id": "toggle_skip", "text": "⏩ Пропускать"}


def _flat(markup):
    return [(b.text, b.callback_data) for row in markup.inline_keyboard for b in row]


def test_skip_button_appears_in_pick_mode():
    """
    Ранний return отдавал клавиатуру до обычных кнопок, поэтому «Пропускать»
    в пик-режиме не было, а настройка show_skip_button тут не работала.
    """
    labels = [t for t, _ in _flat(build_card_keyboard(_pick_card([_DONT_KNOW, _SKIP]), "l1"))]
    assert "⏩ Пропускать" in labels, labels
    assert "❓ Не знаю" in labels


def test_skip_button_obeys_the_setting():
    labels = [t for t, _ in _flat(build_card_keyboard(_pick_card([_DONT_KNOW]), "l1"))]
    assert "⏩ Пропускать" not in labels, labels


def test_dont_know_sends_pick_answer_not_show_answer():
    """Незнание засчитывается: это pick_answer с dont_know, а не показ ответа."""
    data = dict(_flat(build_card_keyboard(_pick_card([_DONT_KNOW]), "l1")))
    assert data["❓ Не знаю"] == "study:l1:pick:dont_know"


def test_skip_sends_toggle_skip():
    data = dict(_flat(build_card_keyboard(_pick_card([_DONT_KNOW, _SKIP]), "l1")))
    assert data["⏩ Пропускать"] == "study:l1:toggle_skip"


def test_button_text_comes_from_the_card():
    card = _pick_card([{"id": "pick_dont_know", "text": "❓ Понятия не имею"}])
    labels = [t for t, _ in _flat(build_card_keyboard(card, "l1"))]
    assert "❓ Понятия не имею" in labels

