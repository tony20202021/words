"""Unit tests for BLS GET /help endpoint."""

import pytest
from app.routers.info import get_help
from common.help_text import HELP_TEXT


@pytest.mark.asyncio
async def test_get_help_returns_text():
    result = await get_help()
    assert "text" in result
    assert result["text"] == HELP_TEXT


@pytest.mark.asyncio
async def test_get_help_text_is_non_empty():
    result = await get_help()
    assert len(result["text"]) > 50


@pytest.mark.asyncio
async def test_get_help_text_contains_key_sections():
    result = await get_help()
    text = result["text"]
    assert "Справка" in text
    assert "интервального повторения" in text
