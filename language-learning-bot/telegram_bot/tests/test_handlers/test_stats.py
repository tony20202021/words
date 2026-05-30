"""Unit tests for /stats handler."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


def _make_message():
    msg = MagicMock()
    msg.answer = AsyncMock()
    return msg


def _make_bls(languages=None, stats_by_lang=None, chart_data=None):
    bls = AsyncMock()
    bls.get_languages = AsyncMock(return_value=languages if languages is not None else [
        {"id": "lang1", "name_ru": "Английский", "name_foreign": "English"},
        {"id": "lang2", "name_ru": "Китайский",  "name_foreign": "中文"},
    ])
    default_stats = {
        "total_words": 100, "words_studied": 50, "words_known": 45,
        "words_skipped": 2, "words_unknown": 3,
        "words_for_today": 3, "progress_percentage": 50.0,
    }
    stats_by_lang = stats_by_lang or {}

    async def get_statistics(user_id, lang_id):
        return stats_by_lang.get(lang_id, default_stats)

    bls.get_statistics = get_statistics
    # chart returns None by default (no charts available)
    bls.get_chart = AsyncMock(return_value=chart_data)
    return bls


# ── basic output ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_stats_no_languages():
    from app.bot.handlers.stats import cmd_stats
    bls = _make_bls(languages=[])
    msg = _make_message()
    with patch("app.bot.handlers.stats.get_bls_client", return_value=bls):
        await cmd_stats(msg, bls_user_id="u1")
    msg.answer.assert_called_once()
    assert "нет" in msg.answer.call_args[0][0].lower()


@pytest.mark.asyncio
async def test_stats_shows_all_languages():
    from app.bot.handlers.stats import cmd_stats
    bls = _make_bls()
    msg = _make_message()
    with patch("app.bot.handlers.stats.get_bls_client", return_value=bls):
        await cmd_stats(msg, bls_user_id="u1")
    text = msg.answer.call_args[0][0]
    assert "Английский" in text
    assert "Китайский" in text


@pytest.mark.asyncio
async def test_stats_skips_empty_language():
    from app.bot.handlers.stats import cmd_stats
    bls = _make_bls(
        stats_by_lang={
            "lang1": {"total_words": 0, "words_studied": 0, "words_known": 0,
                      "words_skipped": 0, "words_for_today": 0, "progress_percentage": 0},
            "lang2": {"total_words": 50, "words_studied": 10, "words_known": 8,
                      "words_skipped": 0, "words_for_today": 2, "progress_percentage": 20.0},
        }
    )
    msg = _make_message()
    with patch("app.bot.handlers.stats.get_bls_client", return_value=bls):
        await cmd_stats(msg, bls_user_id="u1")
    text = msg.answer.call_args[0][0]
    assert "Английский" not in text
    assert "Китайский" in text


@pytest.mark.asyncio
async def test_stats_all_empty_shows_no_data_message():
    from app.bot.handlers.stats import cmd_stats
    empty = {"total_words": 0, "words_studied": 0, "words_known": 0,
             "words_skipped": 0, "words_for_today": 0, "progress_percentage": 0}
    bls = _make_bls(stats_by_lang={"lang1": empty, "lang2": empty})
    msg = _make_message()
    with patch("app.bot.handlers.stats.get_bls_client", return_value=bls):
        await cmd_stats(msg, bls_user_id="u1")
    text = msg.answer.call_args[0][0]
    assert "нет данных" in text.lower() or "начните" in text.lower()


# ── content checks ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_stats_shows_for_today_badge():
    from app.bot.handlers.stats import cmd_stats
    bls = _make_bls(stats_by_lang={
        "lang1": {"total_words": 100, "words_studied": 50, "words_known": 40,
                  "words_skipped": 0, "words_for_today": 7, "progress_percentage": 50.0},
        "lang2": {"total_words": 0, "words_studied": 0, "words_known": 0,
                  "words_skipped": 0, "words_for_today": 0, "progress_percentage": 0},
    })
    msg = _make_message()
    with patch("app.bot.handlers.stats.get_bls_client", return_value=bls):
        await cmd_stats(msg, bls_user_id="u1")
    text = msg.answer.call_args[0][0]
    assert "7" in text
    assert "повторению" in text.lower()


@pytest.mark.asyncio
async def test_stats_shows_all_done_when_no_review():
    from app.bot.handlers.stats import cmd_stats
    bls = _make_bls(stats_by_lang={
        "lang1": {"total_words": 100, "words_studied": 50, "words_known": 48,
                  "words_skipped": 0, "words_for_today": 0, "progress_percentage": 50.0},
        "lang2": {"total_words": 0, "words_studied": 0, "words_known": 0,
                  "words_skipped": 0, "words_for_today": 0, "progress_percentage": 0},
    })
    msg = _make_message()
    with patch("app.bot.handlers.stats.get_bls_client", return_value=bls):
        await cmd_stats(msg, bls_user_id="u1")
    text = msg.answer.call_args[0][0]
    assert "готово" in text.lower() or "✨" in text


@pytest.mark.asyncio
async def test_stats_does_not_send_charts():
    """cmd_stats only sends text — charts are sent by select_language after language selection."""
    from app.bot.handlers.stats import cmd_stats
    bls = _make_bls(chart_data=b"\x89PNG fake image")
    msg = _make_message()
    msg.answer_photo = AsyncMock()
    with patch("app.bot.handlers.stats.get_bls_client", return_value=bls):
        await cmd_stats(msg, bls_user_id="u1")
    msg.answer_photo.assert_not_called()
    msg.answer.assert_called()


@pytest.mark.asyncio
async def test_stats_no_charts_when_bls_returns_none():
    """When BLS returns None for charts, answer_photo should NOT be called."""
    from app.bot.handlers.stats import cmd_stats
    bls = _make_bls(chart_data=None)
    msg = _make_message()
    msg.answer_photo = AsyncMock()
    with patch("app.bot.handlers.stats.get_bls_client", return_value=bls):
        await cmd_stats(msg, bls_user_id="u1")
    msg.answer_photo.assert_not_called()


@pytest.mark.asyncio
async def test_stats_chart_error_doesnt_break_stats():
    """Chart fetch exception must not prevent text stats from being sent."""
    from app.bot.handlers.stats import cmd_stats
    bls = _make_bls()
    bls.get_chart = AsyncMock(side_effect=Exception("network error"))
    msg = _make_message()
    msg.answer_photo = AsyncMock()
    with patch("app.bot.handlers.stats.get_bls_client", return_value=bls):
        await cmd_stats(msg, bls_user_id="u1")
    # text stats must have been sent
    msg.answer.assert_called()
    msg.answer_photo.assert_not_called()


@pytest.mark.asyncio
async def test_stats_shows_pct_known():
    from app.bot.handlers.stats import cmd_stats
    bls = _make_bls(stats_by_lang={
        "lang1": {"total_words": 100, "words_studied": 50, "words_known": 40,
                  "words_skipped": 2, "words_for_today": 0, "progress_percentage": 50.0},
        "lang2": {"total_words": 0, "words_studied": 0, "words_known": 0,
                  "words_skipped": 0, "words_for_today": 0, "progress_percentage": 0},
    })
    msg = _make_message()
    with patch("app.bot.handlers.stats.get_bls_client", return_value=bls):
        await cmd_stats(msg, bls_user_id="u1")
    text = msg.answer.call_args[0][0]
    assert "80.0" in text  # 40/50 * 100
    assert "изучено" in text.lower()
