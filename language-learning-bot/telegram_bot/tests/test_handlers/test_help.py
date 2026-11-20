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
    msg.answer.assert_called_once_with(expected, parse_mode="HTML",
                                       disable_web_page_preview=True)


@pytest.mark.asyncio
async def test_cmd_help_shows_the_sources_link_without_a_preview_card():
    """В справке ссылка на источники данных; карточка-превью GitHub под
    справкой была бы крупнее самой справки."""
    from app.bot.handlers.help import cmd_help
    from common.help_text import HELP_TEXT, DATA_SOURCES_URL
    mock_bls = MagicMock()
    mock_bls.get_help = AsyncMock(return_value={"text": HELP_TEXT})
    msg = MagicMock()
    msg.answer = AsyncMock()
    with patch("app.bot.handlers.help.get_bls_client", return_value=mock_bls):
        await cmd_help(msg)
    args, kwargs = msg.answer.call_args
    assert DATA_SOURCES_URL in args[0]
    assert kwargs.get("disable_web_page_preview") is True


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
