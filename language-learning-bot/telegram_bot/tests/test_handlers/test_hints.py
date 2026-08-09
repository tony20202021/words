"""Тесты меню подсказок (app/bot/handlers/hints.py).

Модуль на 160 строк не был покрыт ни одним тестом: grep 'hints' по tests/ не
давал совпадений.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.bot.handlers.hints import (
    hint_menu, hint_save, HintState,
    ALL_HINT_TYPES, _hint_code, _hint_type_by_code,
    _hint_menu_kb, _hint_menu_text, _get_enabled_hint_types,
)
from common.hint_catalog import setting_key_for

LANG_ID = "507f1f77bcf86cd799439011"
WORD_ID = "507f191e810c19729de860ea"


def _make_callback(data: str):
    cb = MagicMock()
    cb.data = data
    cb.message = MagicMock()
    cb.message.edit_text = AsyncMock()
    cb.message.delete = AsyncMock()
    cb.message.answer = AsyncMock()
    cb.answer = AsyncMock()
    return cb


def _make_message(text=""):
    msg = MagicMock()
    msg.text = text
    msg.answer = AsyncMock()
    return msg


def _make_state(data=None):
    state = MagicMock()
    state.get_data = AsyncMock(return_value=data or {})
    state.update_data = AsyncMock()
    state.set_state = AsyncMock()
    state.clear = AsyncMock()
    return state


def _make_bls(hints=None, enabled=True, save_ok=True):
    bls = AsyncMock()
    bls.get_word_hints = AsyncMock(return_value=hints or {})
    bls.get_hint_settings = AsyncMock(return_value={
        setting_key_for(ht): enabled for ht in ALL_HINT_TYPES
    })
    bls.set_word_hint = AsyncMock(return_value=save_ok)
    bls.delete_word_hint = AsyncMock(return_value=True)
    return bls


def _callbacks(kb):
    return [b.callback_data for row in kb.inline_keyboard for b in row]


# ── коды типов подсказок ─────────────────────────────────────────────────────

class TestHintCodes:
    @pytest.mark.parametrize("hint_type", list(ALL_HINT_TYPES))
    def test_code_roundtrip(self, hint_type):
        assert _hint_type_by_code(_hint_code(hint_type)) == hint_type

    def test_unknown_code_is_empty(self):
        assert _hint_type_by_code("99") == ""

    def test_non_numeric_code_is_empty(self):
        assert _hint_type_by_code("meaning") == ""


# ── клавиатура и текст меню ──────────────────────────────────────────────────

class TestHintMenuKeyboard:
    def test_one_row_per_enabled_type_plus_back(self):
        kb = _hint_menu_kb(LANG_ID, WORD_ID, {}, ALL_HINT_TYPES)
        assert len(kb.inline_keyboard) == len(ALL_HINT_TYPES) + 1
        assert _callbacks(kb)[-1] == f"hint:{LANG_ID}:{WORD_ID}:back"

    def test_delete_button_only_for_filled_hints(self):
        first = next(iter(ALL_HINT_TYPES))
        kb = _hint_menu_kb(LANG_ID, WORD_ID, {first: "текст"}, ALL_HINT_TYPES)
        del_cbs = [c for c in _callbacks(kb) if ":del:" in c]
        assert del_cbs == [f"hint:{LANG_ID}:{WORD_ID}:del:{_hint_code(first)}"]

    def test_blank_hint_counts_as_empty(self):
        first = next(iter(ALL_HINT_TYPES))
        kb = _hint_menu_kb(LANG_ID, WORD_ID, {first: "   "}, ALL_HINT_TYPES)
        assert not [c for c in _callbacks(kb) if ":del:" in c]

    def test_menu_text_shows_value_and_placeholder(self):
        first = next(iter(ALL_HINT_TYPES))
        text = _hint_menu_text(WORD_ID, {first: "моя подсказка"}, ALL_HINT_TYPES)
        assert "моя подсказка" in text
        assert "не задано" in text


# ── фильтр включённых типов ──────────────────────────────────────────────────

class TestEnabledHintTypes:
    @pytest.mark.asyncio
    async def test_only_enabled_types_returned(self):
        first = next(iter(ALL_HINT_TYPES))
        bls = AsyncMock()
        bls.get_hint_settings = AsyncMock(return_value={setting_key_for(first): True})
        enabled = await _get_enabled_hint_types(bls, "u1", LANG_ID)
        assert list(enabled) == [first]

    @pytest.mark.asyncio
    async def test_bls_failure_disables_everything(self):
        bls = AsyncMock()
        bls.get_hint_settings = AsyncMock(side_effect=RuntimeError("bls down"))
        assert await _get_enabled_hint_types(bls, "u1", LANG_ID) == {}


# ── хендлер меню ─────────────────────────────────────────────────────────────

class TestHintMenuHandler:
    @pytest.mark.asyncio
    async def test_show_renders_menu(self):
        bls = _make_bls(hints={"meaning": "ассоциация"})
        cb = _make_callback(f"hint:{LANG_ID}:{WORD_ID}:show")
        with patch("app.bot.handlers.hints.get_bls_client", return_value=bls):
            await hint_menu(cb, _make_state(), bls_user_id="u1")
        cb.message.edit_text.assert_called_once()
        assert "ассоциация" in cb.message.edit_text.call_args.args[0]

    @pytest.mark.asyncio
    async def test_show_alerts_when_all_types_disabled(self):
        bls = _make_bls(enabled=False)
        cb = _make_callback(f"hint:{LANG_ID}:{WORD_ID}:show")
        with patch("app.bot.handlers.hints.get_bls_client", return_value=bls):
            await hint_menu(cb, _make_state(), bls_user_id="u1")
        cb.message.edit_text.assert_not_called()
        assert cb.answer.call_args.kwargs.get("show_alert") is True

    @pytest.mark.asyncio
    async def test_back_deletes_message_and_clears_state(self):
        bls = _make_bls()
        cb = _make_callback(f"hint:{LANG_ID}:{WORD_ID}:back")
        state = _make_state()
        with patch("app.bot.handlers.hints.get_bls_client", return_value=bls):
            await hint_menu(cb, state, bls_user_id="u1")
        cb.message.delete.assert_called_once()
        state.clear.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_calls_bls_with_real_hint_type(self):
        """В callback_data едет номер типа — хендлер обязан развернуть его в имя,
        иначе BLS получит '0' вместо 'meaning'."""
        first = next(iter(ALL_HINT_TYPES))
        bls = _make_bls(hints={first: "текст"})
        cb = _make_callback(f"hint:{LANG_ID}:{WORD_ID}:del:{_hint_code(first)}")
        with patch("app.bot.handlers.hints.get_bls_client", return_value=bls):
            await hint_menu(cb, _make_state(), bls_user_id="u1")
        bls.delete_word_hint.assert_called_once_with("u1", WORD_ID, first)

    @pytest.mark.asyncio
    async def test_edit_sets_state_with_real_hint_type(self):
        first = next(iter(ALL_HINT_TYPES))
        bls = _make_bls()
        cb = _make_callback(f"hint:{LANG_ID}:{WORD_ID}:edit:{_hint_code(first)}")
        state = _make_state()
        with patch("app.bot.handlers.hints.get_bls_client", return_value=bls):
            await hint_menu(cb, state, bls_user_id="u1")
        state.set_state.assert_called_once_with(HintState.input_text)
        assert state.update_data.call_args.kwargs["hint_type"] == first
        assert state.update_data.call_args.kwargs["word_id"] == WORD_ID

    @pytest.mark.asyncio
    async def test_unknown_action_just_answers(self):
        bls = _make_bls()
        cb = _make_callback(f"hint:{LANG_ID}:{WORD_ID}:whatever")
        with patch("app.bot.handlers.hints.get_bls_client", return_value=bls):
            await hint_menu(cb, _make_state(), bls_user_id="u1")
        cb.message.edit_text.assert_not_called()
        cb.answer.assert_called_once()


# ── сохранение текста ────────────────────────────────────────────────────────

class TestHintSave:
    @pytest.mark.asyncio
    async def test_saves_and_shows_menu(self):
        first = next(iter(ALL_HINT_TYPES))
        bls = _make_bls(hints={first: "новая"})
        msg = _make_message("новая")
        state = _make_state({"word_id": WORD_ID, "language_id": LANG_ID,
                             "hint_type": first})
        with patch("app.bot.handlers.hints.get_bls_client", return_value=bls):
            await hint_save(msg, state, bls_user_id="u1")
        bls.set_word_hint.assert_called_once_with(
            "u1", WORD_ID, first, "новая", language_id=LANG_ID)
        assert "сохранена" in msg.answer.call_args.args[0]

    @pytest.mark.asyncio
    async def test_empty_text_rejected_without_clearing_state(self):
        first = next(iter(ALL_HINT_TYPES))
        bls = _make_bls()
        msg = _make_message("   ")
        state = _make_state({"word_id": WORD_ID, "language_id": LANG_ID,
                             "hint_type": first})
        with patch("app.bot.handlers.hints.get_bls_client", return_value=bls):
            await hint_save(msg, state, bls_user_id="u1")
        bls.set_word_hint.assert_not_called()
        state.clear.assert_not_called()

    @pytest.mark.asyncio
    async def test_save_failure_reported(self):
        first = next(iter(ALL_HINT_TYPES))
        bls = _make_bls(save_ok=False)
        msg = _make_message("текст")
        state = _make_state({"word_id": WORD_ID, "language_id": LANG_ID,
                             "hint_type": first})
        with patch("app.bot.handlers.hints.get_bls_client", return_value=bls):
            await hint_save(msg, state, bls_user_id="u1")
        assert "Не удалось" in msg.answer.call_args.args[0]
