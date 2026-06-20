"""Unit tests for settings handler."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from aiogram.fsm.context import FSMContext


def _make_message():
    msg = MagicMock()
    msg.answer = AsyncMock()
    return msg


def _make_callback(data=""):
    cb = MagicMock()
    cb.data = data
    cb.message = MagicMock()
    cb.message.edit_text = AsyncMock()
    cb.answer = AsyncMock()
    return cb


def _make_state(language_id="lang1"):
    state = AsyncMock(spec=FSMContext)
    state.get_data = AsyncMock(return_value={"language_id": language_id})
    return state


def _make_bls(settings=None):
    bls = AsyncMock()
    bls.get_languages = AsyncMock(return_value=[
        {"id": "lang1", "name_ru": "Английский", "name_foreign": "English"},
    ])
    bls.get_settings = AsyncMock(return_value=settings or {
        "use_check_date": True, "show_sounds": False, "start_word": 1,
        "reset_same_day_hours": 16, "reset_cross_midnight_hours": 6,
        "unknown_limit_new_words": 5, "max_check_interval": 365,
    })
    bls.toggle_setting = AsyncMock(return_value={"use_check_date": False})
    bls.set_setting = AsyncMock(return_value={})
    return bls


# ── /settings command ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_cmd_settings_no_language():
    from app.bot.handlers.settings import cmd_settings
    bls = _make_bls()
    msg = _make_message()
    state = AsyncMock(spec=FSMContext)
    state.get_data = AsyncMock(return_value={})
    with patch("app.bot.handlers.settings.get_bls_client", return_value=bls):
        await cmd_settings(msg, state, bls_user_id="u1")
    msg.answer.assert_called_once()
    assert "язык" in msg.answer.call_args[0][0].lower()
    assert msg.answer.call_args.kwargs.get("reply_markup") is None


@pytest.mark.asyncio
async def test_cmd_settings_shows_keyboard():
    from app.bot.handlers.settings import cmd_settings
    bls = _make_bls()
    msg = _make_message()
    state = _make_state()
    with patch("app.bot.handlers.settings.get_bls_client", return_value=bls):
        await cmd_settings(msg, state, bls_user_id="u1")
    msg.answer.assert_called_once()
    assert msg.answer.call_args.kwargs.get("reply_markup") is not None


@pytest.mark.asyncio
async def test_cmd_settings_includes_language_name():
    from app.bot.handlers.settings import cmd_settings
    bls = _make_bls()
    msg = _make_message()
    state = _make_state()
    with patch("app.bot.handlers.settings.get_bls_client", return_value=bls):
        await cmd_settings(msg, state, bls_user_id="u1")
    text = msg.answer.call_args[0][0]
    assert "Английский" in text


# ── toggle callback ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_toggle_setting_calls_bls():
    from app.bot.handlers.settings import toggle_setting
    bls = _make_bls()
    cb = _make_callback("settings:lang1:use_check_date")
    state = _make_state()
    with patch("app.bot.handlers.settings.get_bls_client", return_value=bls):
        await toggle_setting(cb, state, bls_user_id="u1")
    bls.toggle_setting.assert_called_once_with("u1", "lang1", "use_check_date")
    cb.message.edit_text.assert_called_once()
    cb.answer.assert_called_once()


@pytest.mark.asyncio
async def test_toggle_setting_updates_keyboard():
    from app.bot.handlers.settings import toggle_setting
    bls = _make_bls()
    bls.toggle_setting = AsyncMock(return_value={
        "use_check_date": False, "show_sounds": True, "start_word": 1,
        "reset_same_day_hours": 16, "reset_cross_midnight_hours": 6,
        "unknown_limit_new_words": 5, "max_check_interval": 365,
    })
    cb = _make_callback("settings:lang1:use_check_date")
    state = _make_state()
    with patch("app.bot.handlers.settings.get_bls_client", return_value=bls):
        await toggle_setting(cb, state, bls_user_id="u1")
    assert cb.message.edit_text.call_args.kwargs.get("reply_markup") is not None


# ── numeric setting callbacks ─────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_change_numeric_increment():
    from app.bot.handlers.settings import change_numeric_setting
    bls = _make_bls(settings={"start_word": 3, "reset_same_day_hours": 16,
                               "reset_cross_midnight_hours": 6, "unknown_limit_new_words": 0})
    cb = _make_callback("set_num:lang1:start_word:1")
    with patch("app.bot.handlers.settings.get_bls_client", return_value=bls):
        await change_numeric_setting(cb, bls_user_id="u1")
    bls.set_setting.assert_called_once_with("u1", "lang1", "start_word", 4)
    cb.message.edit_text.assert_called_once()


@pytest.mark.asyncio
async def test_change_numeric_decrement():
    from app.bot.handlers.settings import change_numeric_setting
    bls = _make_bls(settings={"start_word": 5, "reset_same_day_hours": 16,
                               "reset_cross_midnight_hours": 6, "unknown_limit_new_words": 0})
    cb = _make_callback("set_num:lang1:start_word:-1")
    with patch("app.bot.handlers.settings.get_bls_client", return_value=bls):
        await change_numeric_setting(cb, bls_user_id="u1")
    bls.set_setting.assert_called_once_with("u1", "lang1", "start_word", 4)


@pytest.mark.asyncio
async def test_change_numeric_clamped_at_min():
    from app.bot.handlers.settings import change_numeric_setting
    # start_word min is 1, decrementing from 1 should stay at 1
    bls = _make_bls(settings={"start_word": 1, "reset_same_day_hours": 16,
                               "reset_cross_midnight_hours": 6, "unknown_limit_new_words": 0})
    cb = _make_callback("set_num:lang1:start_word:-1")
    with patch("app.bot.handlers.settings.get_bls_client", return_value=bls):
        await change_numeric_setting(cb, bls_user_id="u1")
    bls.set_setting.assert_called_once_with("u1", "lang1", "start_word", 1)


@pytest.mark.asyncio
async def test_change_numeric_zero_clamped_for_reset_same_day_hours():
    from app.bot.handlers.settings import change_numeric_setting
    bls = _make_bls(settings={"start_word": 1, "reset_same_day_hours": 0,
                               "reset_cross_midnight_hours": 6, "unknown_limit_new_words": 0})
    cb = _make_callback("set_num:lang1:reset_same_day_hours:-1")
    with patch("app.bot.handlers.settings.get_bls_client", return_value=bls):
        await change_numeric_setting(cb, bls_user_id="u1")
    bls.set_setting.assert_called_once_with("u1", "lang1", "reset_same_day_hours", 0)


# ── noop callback ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_noop_just_answers():
    from app.bot.handlers.settings import noop_callback
    cb = _make_callback("noop")
    await noop_callback(cb)
    cb.answer.assert_called_once()
    cb.message.edit_text.assert_not_called()


# ── keyboard contains numeric settings ────────────────────────────────────────

def test_settings_keyboard_contains_numeric_rows():
    from app.bot.handlers.settings import _build_settings_keyboard
    settings = {"start_word": 3, "reset_same_day_hours": 16,
                "reset_cross_midnight_hours": 6, "unknown_limit_new_words": 10,
                "max_check_interval": 365}
    kb = _build_settings_keyboard(settings, "lang1")
    all_texts = [b.text for row in kb.inline_keyboard for b in row]
    # Display buttons show current values
    assert any("3" in t for t in all_texts)
    all_cbs = [b.callback_data for row in kb.inline_keyboard for b in row]
    assert any("set_num:lang1:start_word:1" in c for c in all_cbs)
    assert any("set_num:lang1:start_word:-1" in c for c in all_cbs)
