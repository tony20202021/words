"""Unit tests for /help handler."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.mark.asyncio
async def test_cmd_help_sends_text():
    from app.bot.handlers.help import cmd_help, _BOT_COMMANDS
    mock_bls = MagicMock()
    mock_bls.get_help = AsyncMock(return_value={"text": "Текст справки"})
    msg = MagicMock()
    msg.answer = AsyncMock()
    with patch("app.bot.handlers.help.get_bls_client", return_value=mock_bls):
        await cmd_help(msg)
    expected = "Текст справки" + _BOT_COMMANDS
    msg.answer.assert_called_once_with(expected, parse_mode="HTML")


@pytest.mark.asyncio
async def test_cmd_help_mentions_key_commands():
    from app.bot.handlers.help import cmd_help, _BOT_COMMANDS
    mock_bls = MagicMock()
    mock_bls.get_help = AsyncMock(return_value={"text": "Текст справки"})
    msg = MagicMock()
    msg.answer = AsyncMock()
    with patch("app.bot.handlers.help.get_bls_client", return_value=mock_bls):
        await cmd_help(msg)
    for cmd in ("/study", "/settings", "/stats", "/language"):
        assert cmd in _BOT_COMMANDS


@pytest.mark.asyncio
async def test_cmd_help_fallback_on_bls_error():
    from app.bot.handlers.help import cmd_help, _BOT_COMMANDS
    mock_bls = MagicMock()
    mock_bls.get_help = AsyncMock(return_value={})
    msg = MagicMock()
    msg.answer = AsyncMock()
    with patch("app.bot.handlers.help.get_bls_client", return_value=mock_bls):
        await cmd_help(msg)
    call_args = msg.answer.call_args
    assert "Справка недоступна." in call_args[0][0]
    assert _BOT_COMMANDS in call_args[0][0]
