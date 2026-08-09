"""Все callback_data должны укладываться в лимит Telegram — 64 байта.

Кнопка с более длинным callback_data не просто не работает: Telegram отвечает
на sendMessage ошибкой и не отправляет сообщение целиком. В фикстурах остальных
тестов id вида "lang1"/"w1", поэтому проблема там не проявляется, а в бою и
language_id, и word_id — это ObjectId по 24 символа.
"""

import pytest

from app.bot.keyboards import build_card_keyboard
from app.bot.handlers.hints import _hint_menu_kb, ALL_HINT_TYPES
from app.bot.handlers.settings import _build_settings_keyboard, SETTING_LABELS, NUMERIC_LABELS
from tests.conftest import make_card

TG_CALLBACK_LIMIT = 64

LANG_ID = "507f1f77bcf86cd799439011"   # ObjectId, 24 символа
WORD_ID = "507f191e810c19729de860ea"
OTHER_WORD_ID = "5f2b8c1e9d4a3b7c6e5d4f30"


def _all_callbacks(keyboard):
    return [b.callback_data for row in keyboard.inline_keyboard for b in row
            if b.callback_data]


def _assert_within_limit(keyboard):
    too_long = [(cb, len(cb.encode())) for cb in _all_callbacks(keyboard)
                if len(cb.encode()) > TG_CALLBACK_LIMIT]
    assert not too_long, f"callback_data длиннее {TG_CALLBACK_LIMIT} байт: {too_long}"


def _card_with_hints(**kwargs):
    card = make_card(**kwargs)
    card["meta"]["word_id"] = WORD_ID
    card["meta"]["hint_enabled_types"] = list(ALL_HINT_TYPES)
    return card


def _pick_card():
    card = make_card(show_answer=False)
    card["pick_options"] = {
        "target_modality": "translation",
        "options": [
            {"word_id": WORD_ID, "target_text": "привет"},
            {"word_id": OTHER_WORD_ID, "target_text": "пока"},
        ],
    }
    return card


class TestCardKeyboardLimits:
    def test_card_before_answer(self):
        _assert_within_limit(build_card_keyboard(_card_with_hints(show_answer=False), LANG_ID))

    def test_card_after_answer_with_hint_button(self):
        _assert_within_limit(build_card_keyboard(_card_with_hints(show_answer=True), LANG_ID))

    def test_card_with_sounds(self):
        card = _card_with_hints(show_answer=False)
        card["sounds"] = ["a.mp3", "b.mp3"]
        _assert_within_limit(build_card_keyboard(card, LANG_ID))

    def test_pick_mode_options(self):
        _assert_within_limit(build_card_keyboard(_pick_card(), LANG_ID))

    def test_pick_mode_sound_modality(self):
        card = _pick_card()
        card["pick_options"]["target_modality"] = "sound"
        _assert_within_limit(build_card_keyboard(card, LANG_ID))

    def test_ban_distractor_button(self):
        card = _card_with_hints(show_answer=True)
        card["last_wrong_distractor_id"] = OTHER_WORD_ID
        _assert_within_limit(build_card_keyboard(card, LANG_ID))

    def test_clear_forbidden_pairs_button(self):
        card = _card_with_hints(show_answer=True)
        card["extra_content"] = [{"type": "forbidden_quiz_pairs",
                                  "word_ids": [OTHER_WORD_ID],
                                  "group": "forbidden_quiz_pairs"}]
        _assert_within_limit(build_card_keyboard(card, LANG_ID))


class TestHintKeyboardLimits:
    def test_hint_menu_all_types_empty(self):
        kb = _hint_menu_kb(LANG_ID, WORD_ID, {}, ALL_HINT_TYPES)
        _assert_within_limit(kb)

    def test_hint_menu_all_types_filled_adds_delete_buttons(self):
        hints = {ht: "текст" for ht in ALL_HINT_TYPES}
        kb = _hint_menu_kb(LANG_ID, WORD_ID, hints, ALL_HINT_TYPES)
        _assert_within_limit(kb)

    @pytest.mark.parametrize("hint_type", list(ALL_HINT_TYPES))
    def test_each_hint_type_fits(self, hint_type):
        subset = {hint_type: ALL_HINT_TYPES[hint_type]}
        kb = _hint_menu_kb(LANG_ID, WORD_ID, {hint_type: "текст"}, subset)
        _assert_within_limit(kb)


class TestSettingsKeyboardLimits:
    def test_settings_keyboard(self):
        settings = {k: True for k in SETTING_LABELS}
        settings.update({k: 5 for k in NUMERIC_LABELS})
        _assert_within_limit(_build_settings_keyboard(settings, LANG_ID))
