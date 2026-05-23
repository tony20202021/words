"""Unit tests for Telegram bot admin handler."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from aiogram.fsm.context import FSMContext
from app.bot.handlers.admin import (
    cmd_admin, admin_stats, admin_users, admin_broadcast_start,
    admin_menu_back, AdminState,
)


def _make_message(text="", user_id="u1"):
    msg = MagicMock()
    msg.text = text
    msg.from_user = MagicMock(id=111)
    msg.answer = AsyncMock()
    return msg


def _make_callback(data="", user_id="u1"):
    cb = MagicMock()
    cb.data = data
    cb.from_user = MagicMock(id=111)
    cb.message = MagicMock()
    cb.message.edit_text = AsyncMock()
    cb.answer = AsyncMock()
    return cb


def _make_state():
    state = AsyncMock(spec=FSMContext)
    state.get_data = AsyncMock(return_value={})
    state.set_state = AsyncMock()
    state.clear = AsyncMock()
    return state


def _make_bls(is_admin=True):
    bls = AsyncMock()
    bls.is_admin = AsyncMock(return_value=is_admin)
    bls.admin_global_stats = AsyncMock(return_value={
        "total_users": 7,
        "languages": [
            {"id": "lang1", "name_ru": "Китайский", "name_foreign": "中文",
             "word_count": 100, "active_users": 3},
        ],
    })
    bls.admin_list_users = AsyncMock(return_value={
        "users": [
            {"id": "u1", "first_name": "Alice", "last_name": None,
             "username": "alice", "telegram_id": 111, "is_admin": False},
        ],
        "page": 1, "total_pages": 1,
    })
    return bls


# ── /admin command ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_cmd_admin_not_admin():
    bls = _make_bls(is_admin=False)
    msg = _make_message()
    with patch("app.bot.handlers.admin.get_bls_client", return_value=bls):
        await cmd_admin(msg, bls_user_id="u1")
    msg.answer.assert_called_once()
    assert "нет прав" in msg.answer.call_args[0][0].lower()


@pytest.mark.asyncio
async def test_cmd_admin_shows_menu():
    bls = _make_bls()
    msg = _make_message()
    with patch("app.bot.handlers.admin.get_bls_client", return_value=bls):
        await cmd_admin(msg, bls_user_id="u1")
    msg.answer.assert_called_once()
    call_kwargs = msg.answer.call_args
    assert "reply_markup" in call_kwargs.kwargs or len(call_kwargs.args) > 1 or call_kwargs.kwargs.get("reply_markup")


# ── admin:stats callback ──────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_admin_stats_shows_counts():
    bls = _make_bls()
    cb = _make_callback("admin:stats")
    with patch("app.bot.handlers.admin.get_bls_client", return_value=bls):
        await admin_stats(cb, bls_user_id="u1")
    cb.message.edit_text.assert_called_once()
    text = cb.message.edit_text.call_args[0][0]
    assert "7" in text  # total_users
    assert "Китайский" in text


@pytest.mark.asyncio
async def test_admin_stats_forbidden():
    bls = _make_bls(is_admin=False)
    cb = _make_callback("admin:stats")
    with patch("app.bot.handlers.admin.get_bls_client", return_value=bls):
        await admin_stats(cb, bls_user_id="u1")
    cb.answer.assert_called_once_with("Нет доступа", show_alert=True)
    cb.message.edit_text.assert_not_called()


# ── admin:users callback ──────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_admin_users_shows_list():
    bls = _make_bls()
    cb = _make_callback("admin:users:1")
    with patch("app.bot.handlers.admin.get_bls_client", return_value=bls):
        await admin_users(cb, bls_user_id="u1")
    cb.message.edit_text.assert_called_once()
    text = cb.message.edit_text.call_args[0][0]
    assert "Alice" in text


@pytest.mark.asyncio
async def test_admin_users_page_passed_to_bls():
    bls = _make_bls()
    cb = _make_callback("admin:users:3")
    with patch("app.bot.handlers.admin.get_bls_client", return_value=bls):
        await admin_users(cb, bls_user_id="u1")
    bls.admin_list_users.assert_called_once_with("u1", 3)


# ── broadcast start ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_admin_broadcast_start_sets_state():
    bls = _make_bls()
    cb = _make_callback("admin:broadcast")
    state = _make_state()
    with patch("app.bot.handlers.admin.get_bls_client", return_value=bls):
        await admin_broadcast_start(cb, state, bls_user_id="u1")
    state.set_state.assert_called_once_with(AdminState.broadcast_input)
    cb.message.edit_text.assert_called_once()


@pytest.mark.asyncio
async def test_admin_broadcast_forbidden():
    bls = _make_bls(is_admin=False)
    cb = _make_callback("admin:broadcast")
    state = _make_state()
    with patch("app.bot.handlers.admin.get_bls_client", return_value=bls):
        await admin_broadcast_start(cb, state, bls_user_id="u1")
    state.set_state.assert_not_called()
    cb.answer.assert_called_once_with("Нет доступа", show_alert=True)


# ── back to menu ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_admin_menu_back_clears_state():
    bls = _make_bls()
    cb = _make_callback("admin:menu")
    state = _make_state()
    with patch("app.bot.handlers.admin.get_bls_client", return_value=bls):
        await admin_menu_back(cb, state, bls_user_id="u1")
    state.clear.assert_called_once()
    cb.message.edit_text.assert_called_once()
