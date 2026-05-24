"""Unit tests for auth confirm/deny callback handler."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


def _make_callback(data=""):
    cb = MagicMock()
    cb.data = data
    cb.message = MagicMock()
    cb.message.edit_text = AsyncMock()
    cb.answer = AsyncMock()
    return cb


def _make_bls(confirm_ok=True, confirm_reason=None):
    bls = AsyncMock()
    result = {"ok": confirm_ok}
    if confirm_reason:
        result["reason"] = confirm_reason
    bls.auth_confirm = AsyncMock(return_value=result)
    bls.auth_deny = AsyncMock(return_value={"ok": True})
    return bls


# ── confirm ───────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_auth_confirm_success():
    from app.bot.handlers.auth import handle_auth_callback
    bls = _make_bls(confirm_ok=True)
    cb = _make_callback("auth:confirm:tok-abc")
    with patch("app.bot.handlers.auth.get_bls_client", return_value=bls):
        await handle_auth_callback(cb)
    bls.auth_confirm.assert_called_once_with("tok-abc")
    cb.message.edit_text.assert_called_once()
    text = cb.message.edit_text.call_args[0][0]
    assert "✅" in text or "подтвержден" in text.lower()


@pytest.mark.asyncio
async def test_auth_confirm_expired_token():
    from app.bot.handlers.auth import handle_auth_callback
    bls = _make_bls(confirm_ok=False, confirm_reason="expired")
    cb = _make_callback("auth:confirm:tok-old")
    with patch("app.bot.handlers.auth.get_bls_client", return_value=bls):
        await handle_auth_callback(cb)
    text = cb.message.edit_text.call_args[0][0]
    assert "устарел" in text.lower() or "expired" in text.lower()


@pytest.mark.asyncio
async def test_auth_confirm_invalid_token():
    from app.bot.handlers.auth import handle_auth_callback
    bls = _make_bls(confirm_ok=False)
    cb = _make_callback("auth:confirm:tok-bad")
    with patch("app.bot.handlers.auth.get_bls_client", return_value=bls):
        await handle_auth_callback(cb)
    text = cb.message.edit_text.call_args[0][0]
    assert "недействителен" in text.lower() or "❌" in text


# ── deny ──────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_auth_deny():
    from app.bot.handlers.auth import handle_auth_callback
    bls = _make_bls()
    cb = _make_callback("auth:deny:tok-abc")
    with patch("app.bot.handlers.auth.get_bls_client", return_value=bls):
        await handle_auth_callback(cb)
    bls.auth_deny.assert_called_once_with("tok-abc")
    cb.message.edit_text.assert_called_once()
    text = cb.message.edit_text.call_args[0][0]
    assert "отклонен" in text.lower() or "❌" in text


# ── malformed data ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_auth_malformed_data_no_crash():
    from app.bot.handlers.auth import handle_auth_callback
    bls = _make_bls()
    cb = _make_callback("auth:confirm")  # missing token
    with patch("app.bot.handlers.auth.get_bls_client", return_value=bls):
        await handle_auth_callback(cb)
    cb.answer.assert_called_once()
    cb.message.edit_text.assert_not_called()
