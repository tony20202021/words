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
    cb.message.answer = AsyncMock()
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
    bls.get_statistics = AsyncMock(return_value={
        "progress_percentage": 0.0, "total_words": 0,
        "words_for_today": 0, "words_studied": 0,
    })
    bls.get_settings = AsyncMock(return_value={})
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
    # Sends multiple messages; the last one carries the navigation keyboard
    msg.answer.assert_called()
    assert any(
        call.kwargs.get("reply_markup") is not None
        for call in msg.answer.call_args_list
    )


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
    msg.answer.assert_called()
    assert any(
        call.kwargs.get("reply_markup") is not None
        for call in msg.answer.call_args_list
    )


# ── /web ──────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_cmd_web_sends_url():
    from app.bot.handlers.start import cmd_web
    msg = _make_message()
    msg.answer_photo = AsyncMock()
    bls = AsyncMock()
    bls.mobile_create_token = AsyncMock(return_value={"code": "ABC123"})
    bls.get_qr_png = AsyncMock(return_value=None)
    with patch.dict(os.environ, {"WEB_URL": "http://example.com:8800"}):
        with patch("app.bot.handlers.start.get_bls_client", return_value=bls):
            await cmd_web(msg, bls_user_id="u1")
    msg.answer.assert_called_once()
    text = msg.answer.call_args[0][0]
    assert "http://example.com:8800/login?code=ABC123" in text
    assert "ABC123" in text


# ── lang: callback ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_select_language_shows_info_and_buttons():
    """Выбор языка → несколько сообщений с инфо и кнопками действий."""
    from app.bot.handlers.start import select_language
    bls = _make_bls()
    cb = _make_callback("lang:lang1")
    state = _make_state()
    with patch("app.bot.handlers.start.get_bls_client", return_value=bls):
        await select_language(cb, state, bls_user_id="u1")
    cb.answer.assert_called_once()
    cb.message.answer.assert_called()
    # Последнее сообщение содержит кнопки действий
    assert any(
        call.kwargs.get("reply_markup") is not None
        for call in cb.message.answer.call_args_list
    )


@pytest.mark.asyncio
async def test_select_language_no_session_management():
    """select_language больше не управляет сессией — вызовы start_session не делается."""
    from app.bot.handlers.start import select_language
    bls = _make_bls()
    cb = _make_callback("lang:lang1")
    state = _make_state()
    with patch("app.bot.handlers.start.get_bls_client", return_value=bls):
        await select_language(cb, state, bls_user_id="u1")
    bls.start_session.assert_not_called()
    bls.get_session.assert_not_called()


@pytest.mark.asyncio
async def test_select_language_no_words_shows_alert():
    """Совместимость: если языка нет в списке — всё равно не падает."""
    from app.bot.handlers.start import select_language
    bls = _make_bls(languages=[{"id": "lang1", "name_ru": "Английский", "name_foreign": "English"}])
    cb = _make_callback("lang:lang1")
    state = _make_state()
    with patch("app.bot.handlers.start.get_bls_client", return_value=bls):
        await select_language(cb, state, bls_user_id="u1")
    cb.answer.assert_called_once()
    cb.message.answer.assert_called()


@pytest.mark.asyncio
async def test_select_language_card_none_shows_alert():
    """Совместимость: select_language не зависит от карточек сессии."""
    from app.bot.handlers.start import select_language
    bls = _make_bls()
    cb = _make_callback("lang:lang1")
    state = _make_state()
    with patch("app.bot.handlers.start.get_bls_client", return_value=bls):
        await select_language(cb, state, bls_user_id="u1")
    cb.answer.assert_called_once()
    cb.message.answer.assert_called()


@pytest.mark.asyncio
async def test_select_language_stores_language_id_in_state():
    from app.bot.handlers.start import select_language
    bls = _make_bls()
    cb = _make_callback("lang:lang2")
    state = _make_state()
    with patch("app.bot.handlers.start.get_bls_client", return_value=bls):
        await select_language(cb, state, bls_user_id="u1")
    state.update_data.assert_called()
    # Ищем вызов, где language_id передан как kwarg
    all_kwargs = [c.kwargs for c in state.update_data.call_args_list]
    assert any(kw.get("language_id") == "lang2" for kw in all_kwargs)
