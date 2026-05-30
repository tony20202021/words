"""Unit tests for Telegram bot admin handler."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from aiogram.fsm.context import FSMContext
from app.bot.handlers.admin import (
    cmd_admin, admin_stats, admin_users, admin_broadcast_start,
    admin_menu_back, AdminState,
    admin_import_start, admin_import_mode, admin_import_file,
    admin_export_range_start, admin_export_range_exec,
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
    bls.admin_export_words = AsyncMock(return_value=b"fake-xlsx-data")
    bls.admin_import_words = AsyncMock(return_value={"ok": True, "imported": {"imported": 42}})
    return bls


def _make_document(filename="words.xlsx", file_id="fid123"):
    doc = MagicMock()
    doc.file_id = file_id
    doc.file_name = filename
    return doc


def _make_message_with_doc(filename="words.xlsx"):
    msg = _make_message()
    msg.document = _make_document(filename)
    msg.answer = AsyncMock(return_value=MagicMock(edit_text=AsyncMock(), delete=AsyncMock()))
    msg.answer_document = AsyncMock()
    # bot mock for file download
    fake_file = MagicMock()
    fake_file.file_path = "documents/file.xlsx"
    msg.bot = AsyncMock()
    msg.bot.get_file = AsyncMock(return_value=fake_file)
    import io
    msg.bot.download_file = AsyncMock(return_value=io.BytesIO(b"fake xlsx content"))
    return msg


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


# ── Import ────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_import_start_shows_mode_menu():
    bls = _make_bls()
    cb = _make_callback("admin:import:lang1")
    state = _make_state()
    with patch("app.bot.handlers.admin.get_bls_client", return_value=bls):
        await admin_import_start(cb, state, bls_user_id="u1")
    cb.message.edit_text.assert_called_once()
    text = cb.message.edit_text.call_args[0][0]
    assert "режим" in text.lower() or "импорт" in text.lower()
    assert cb.message.edit_text.call_args.kwargs.get("reply_markup") is not None


@pytest.mark.asyncio
async def test_import_mode_sets_state():
    bls = _make_bls()
    cb = _make_callback("admin:import_mode:lang1:add")
    state = _make_state()
    with patch("app.bot.handlers.admin.get_bls_client", return_value=bls):
        await admin_import_mode(cb, state, bls_user_id="u1")
    state.set_state.assert_called_once_with(AdminState.import_waiting)
    state.update_data.assert_called_once_with(lang_id="lang1", clear_existing=False)
    cb.message.edit_text.assert_called_once()


@pytest.mark.asyncio
async def test_import_mode_clear_flag():
    bls = _make_bls()
    cb = _make_callback("admin:import_mode:lang1:clear")
    state = _make_state()
    with patch("app.bot.handlers.admin.get_bls_client", return_value=bls):
        await admin_import_mode(cb, state, bls_user_id="u1")
    state.update_data.assert_called_once_with(lang_id="lang1", clear_existing=True)


@pytest.mark.asyncio
async def test_import_file_success():
    bls = _make_bls()
    state = _make_state()
    state.get_data = AsyncMock(return_value={"lang_id": "lang1", "clear_existing": False})
    msg = _make_message_with_doc("words.xlsx")
    with patch("app.bot.handlers.admin.get_bls_client", return_value=bls):
        await admin_import_file(msg, state, bls_user_id="u1")
    bls.admin_import_words.assert_called_once()
    call = bls.admin_import_words.call_args
    assert call.args[0] == "u1"
    assert call.args[1] == "lang1"
    assert call.args[3] == "words.xlsx"
    assert call.args[4] is False  # clear_existing


@pytest.mark.asyncio
async def test_import_file_wrong_extension():
    bls = _make_bls()
    state = _make_state()
    state.get_data = AsyncMock(return_value={"lang_id": "lang1", "clear_existing": False})
    msg = _make_message_with_doc("data.pdf")
    with patch("app.bot.handlers.admin.get_bls_client", return_value=bls):
        await admin_import_file(msg, state, bls_user_id="u1")
    bls.admin_import_words.assert_not_called()
    msg.answer.assert_called()


@pytest.mark.asyncio
async def test_import_forbidden():
    bls = _make_bls(is_admin=False)
    cb = _make_callback("admin:import:lang1")
    state = _make_state()
    with patch("app.bot.handlers.admin.get_bls_client", return_value=bls):
        await admin_import_start(cb, state, bls_user_id="u1")
    cb.answer.assert_called_once_with("Нет доступа", show_alert=True)
    cb.message.edit_text.assert_not_called()


# ── Export with range ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_export_range_start_sets_state():
    bls = _make_bls()
    cb = _make_callback("admin:export_range:lang1:xlsx")
    state = _make_state()
    with patch("app.bot.handlers.admin.get_bls_client", return_value=bls):
        await admin_export_range_start(cb, state, bls_user_id="u1")
    state.set_state.assert_called_once_with(AdminState.export_range_input)
    state.update_data.assert_called_once_with(lang_id="lang1", fmt="xlsx")
    cb.message.edit_text.assert_called_once()


@pytest.mark.asyncio
async def test_export_range_exec_valid():
    bls = _make_bls()
    state = _make_state()
    state.get_data = AsyncMock(return_value={"lang_id": "lang1", "fmt": "xlsx"})
    msg = _make_message("1-100")
    msg.answer = AsyncMock(return_value=MagicMock(edit_text=AsyncMock(), delete=AsyncMock()))
    msg.answer_document = AsyncMock()
    with patch("app.bot.handlers.admin.get_bls_client", return_value=bls):
        await admin_export_range_exec(msg, state, bls_user_id="u1")
    bls.admin_export_words.assert_called_once_with("u1", "lang1", "xlsx", start=1, end=100)
    msg.answer_document.assert_called_once()


@pytest.mark.asyncio
async def test_export_range_exec_invalid_input():
    bls = _make_bls()
    state = _make_state()
    state.get_data = AsyncMock(return_value={"lang_id": "lang1", "fmt": "csv"})
    msg = _make_message("не диапазон")
    msg.answer = AsyncMock()
    with patch("app.bot.handlers.admin.get_bls_client", return_value=bls):
        await admin_export_range_exec(msg, state, bls_user_id="u1")
    bls.admin_export_words.assert_not_called()
    msg.answer.assert_called()
    text = msg.answer.call_args[0][0]
    assert "формат" in text.lower() or "диапазон" in text.lower()
