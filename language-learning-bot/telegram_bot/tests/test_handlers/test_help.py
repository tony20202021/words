"""Unit tests for /help handler."""

import pytest
from unittest.mock import AsyncMock, MagicMock


@pytest.mark.asyncio
async def test_cmd_help_sends_text():
    from app.bot.handlers.help import cmd_help, HELP_TEXT
    msg = MagicMock()
    msg.answer = AsyncMock()
    await cmd_help(msg)
    msg.answer.assert_called_once_with(HELP_TEXT, parse_mode="HTML")


@pytest.mark.asyncio
async def test_cmd_help_mentions_key_commands():
    from app.bot.handlers.help import cmd_help, HELP_TEXT
    msg = MagicMock()
    msg.answer = AsyncMock()
    await cmd_help(msg)
    for cmd in ("/study", "/settings", "/stats", "/language"):
        assert cmd in HELP_TEXT
