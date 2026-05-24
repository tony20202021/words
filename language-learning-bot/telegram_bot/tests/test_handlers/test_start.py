"""Unit tests for start/language handler."""

import pytest
import os
from unittest.mock import AsyncMock, MagicMock, patch
from aiogram.fsm.context import FSMContext
from tests.conftest import make_card, make_session_resp


def _make_message(text=""):
    msg = MagicMock()
    msg.text = text
    msg.from_user = MagicMock(id=111)
    msg.answer = AsyncMock()
    return msg


def _make_callback(data=""):
    cb = MagicMock()
    cb.data = data
    cb.from_user = MagicMock(id=111)
    cb.message = MagicMock()
    cb.message.edit_text = AsyncMock()
    cb.answer = AsyncMock()
    return cb


def _make_state(language_id=None):
    state = AsyncMock(spec=FSMContext)
    state.get_data = AsyncMock(return_value={"language_id": language_id} if language_id else {})
    state.set_state = AsyncMock()
    state.update_data = AsyncMock()
    return state


def _make_bls(languages=None):
    bls = AsyncMock()
    bls.get_languages = AsyncMock(return_value=languages if languages is not None else [
        {"id": "lang1", "name_ru": "Английский", "name_foreign": "English"},
        {"id": "lang2", "name_ru": "Китайский",  "name_foreign": "中文"},
    ])
    bls.get_session = AsyncMock(return_value=None)
    bls.start_session = AsyncMock(return_value=make_session_resp())
    return bls


# ── /start ────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_cmd_start_shows_language_keyboard():
    from app.bot.handlers.start import cmd_start
    bls = _make_bls()
    msg = _make_message()
    state = _make_state()
    with patch("app.bot.handlers.start.get_bls_client", return_value=bls):
        await cmd_start(msg, state, bls_user_id="u1")
    msg.answer.assert_called_once()
    assert msg.answer.call_args.kwargs.get("reply_markup") is not None


@pytest.mark.asyncio
async def test_cmd_start_no_languages():
    from app.bot.handlers.start import cmd_start
    bls = _make_bls(languages=[])
    msg = _make_message()
    state = _make_state()
    with patch("app.bot.handlers.start.get_bls_client", return_value=bls):
        await cmd_start(msg, state, bls_user_id="u1")
    msg.answer.assert_called_once()
    assert "нет" in msg.answer.call_args[0][0].lower()


# ── /language ─────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_cmd_language_shows_keyboard():
    from app.bot.handlers.start import cmd_language
    bls = _make_bls()
    msg = _make_message()
    state = _make_state()
    with patch("app.bot.handlers.start.get_bls_client", return_value=bls):
        await cmd_language(msg, state, bls_user_id="u1")
    msg.answer.assert_called_once()
    assert msg.answer.call_args.kwargs.get("reply_markup") is not None


# ── /web ──────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_cmd_web_sends_url():
    from app.bot.handlers.start import cmd_web
    msg = _make_message()
    msg.from_user.id = 42
    with patch.dict(os.environ, {"WEB_URL": "http://example.com:8800"}):
        await cmd_web(msg)
    msg.answer.assert_called_once()
    text = msg.answer.call_args[0][0]
    assert "http://example.com:8800" in text
    assert "42" in text


# ── lang: callback ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_select_language_starts_session_and_shows_card():
    from app.bot.handlers.start import select_language
    bls = _make_bls()
    cb = _make_callback("lang:lang1")
    state = _make_state()
    with patch("app.bot.handlers.start.get_bls_client", return_value=bls):
        await select_language(cb, state, bls_user_id="u1")
    cb.message.edit_text.assert_called_once()
    cb.answer.assert_called_once()


@pytest.mark.asyncio
async def test_select_language_reuses_existing_session():
    from app.bot.handlers.start import select_language
    bls = _make_bls()
    bls.get_session = AsyncMock(return_value=make_session_resp())
    cb = _make_callback("lang:lang1")
    state = _make_state()
    with patch("app.bot.handlers.start.get_bls_client", return_value=bls):
        await select_language(cb, state, bls_user_id="u1")
    bls.start_session.assert_not_called()
    cb.message.edit_text.assert_called_once()


@pytest.mark.asyncio
async def test_select_language_no_words_shows_alert():
    from app.bot.handlers.start import select_language
    bls = _make_bls()
    bls.get_session = AsyncMock(return_value=None)
    bls.start_session = AsyncMock(return_value=None)
    cb = _make_callback("lang:lang1")
    state = _make_state()
    with patch("app.bot.handlers.start.get_bls_client", return_value=bls):
        await select_language(cb, state, bls_user_id="u1")
    cb.answer.assert_called_once()
    assert cb.answer.call_args.kwargs.get("show_alert") is True
    cb.message.edit_text.assert_not_called()


@pytest.mark.asyncio
async def test_select_language_card_none_shows_alert():
    from app.bot.handlers.start import select_language
    bls = _make_bls()
    bls.start_session = AsyncMock(return_value={"session_id": "s1", "card": None})
    cb = _make_callback("lang:lang1")
    state = _make_state()
    with patch("app.bot.handlers.start.get_bls_client", return_value=bls):
        await select_language(cb, state, bls_user_id="u1")
    cb.answer.assert_called_once()
    assert cb.answer.call_args.kwargs.get("show_alert") is True


@pytest.mark.asyncio
async def test_select_language_stores_language_id_in_state():
    from app.bot.handlers.start import select_language
    bls = _make_bls()
    cb = _make_callback("lang:lang2")
    state = _make_state()
    with patch("app.bot.handlers.start.get_bls_client", return_value=bls):
        await select_language(cb, state, bls_user_id="u1")
    state.update_data.assert_called()
    stored = state.update_data.call_args.kwargs
    assert stored.get("language_id") == "lang2"
