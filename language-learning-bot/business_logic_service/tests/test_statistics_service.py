"""
Unit tests for statistics_service — no I/O, no DB, pure logic with mocked api_client.

Covers:
- update_daily_statistics: create-if-missing snapshot
- create_first_finish_if_missing: seeded at first word of day
- update_daily_max_word_number: always updates both records
- update_daily_first_finish_statistics: always overwrites (session completion)
"""

import pytest
from datetime import date
from unittest.mock import AsyncMock, call

from app.services.statistics_service import (
    update_daily_statistics,
    create_first_finish_if_missing,
    update_daily_max_word_number,
    update_daily_first_finish_statistics,
)


TODAY = date(2026, 6, 7)

PROGRESS = {
    "words_studied": 100,
    "words_known": 90,
    "words_skipped": 0,
    "words_for_today": 20,
    "word_numbers_for_today": [],
    "word_numbers_unknown": [],
    "word_check_interval": [],
}


def make_api(*, daily_exists=False, ff_exists=False):
    """Return a mock api_client for statistics operations."""
    api = AsyncMock()
    api.get_daily_statistics.return_value = {
        "success": True,
        "result": {"words_studied": 100} if daily_exists else None,
    }
    api.get_daily_first_finish_statistics.return_value = {
        "success": True,
        "result": {"words_studied": 100} if ff_exists else None,
    }
    api.update_daily_statistics.return_value = {"success": True, "result": {}}
    api.update_daily_first_finish_statistics.return_value = {"success": True, "result": {}}
    return api


# ── update_daily_statistics ───────────────────────────────────────────────────

class TestUpdateDailyStatistics:
    @pytest.mark.asyncio
    async def test_creates_record_when_none_exists(self):
        api = make_api(daily_exists=False)
        result = await update_daily_statistics("u1", "lang1", TODAY, PROGRESS, api)
        assert result is True
        api.update_daily_statistics.assert_called_once()

    @pytest.mark.asyncio
    async def test_skips_create_when_record_exists(self):
        api = make_api(daily_exists=True)
        result = await update_daily_statistics("u1", "lang1", TODAY, PROGRESS, api)
        assert result is True
        api.update_daily_statistics.assert_not_called()

    @pytest.mark.asyncio
    async def test_returns_false_on_api_error(self):
        api = make_api(daily_exists=False)
        api.update_daily_statistics.return_value = {"success": False, "error": "fail"}
        result = await update_daily_statistics("u1", "lang1", TODAY, PROGRESS, api)
        assert result is False

    @pytest.mark.asyncio
    async def test_creates_when_get_returns_failure(self):
        api = make_api()
        api.get_daily_statistics.return_value = {"success": False, "result": None}
        result = await update_daily_statistics("u1", "lang1", TODAY, PROGRESS, api)
        assert result is True
        api.update_daily_statistics.assert_called_once()


# ── create_first_finish_if_missing ────────────────────────────────────────────

class TestCreateFirstFinishIfMissing:
    @pytest.mark.asyncio
    async def test_creates_when_no_record(self):
        """Seeds first_finish at the first word of the day."""
        api = make_api(ff_exists=False)
        result = await create_first_finish_if_missing("u1", "lang1", TODAY, PROGRESS, api)
        assert result is True
        api.update_daily_first_finish_statistics.assert_called_once()

    @pytest.mark.asyncio
    async def test_skips_when_record_already_exists(self):
        """Does not overwrite existing first_finish snapshot."""
        api = make_api(ff_exists=True)
        result = await create_first_finish_if_missing("u1", "lang1", TODAY, PROGRESS, api)
        assert result is True
        api.update_daily_first_finish_statistics.assert_not_called()

    @pytest.mark.asyncio
    async def test_returns_false_on_api_error(self):
        api = make_api(ff_exists=False)
        api.update_daily_first_finish_statistics.return_value = {"success": False, "error": "fail"}
        result = await create_first_finish_if_missing("u1", "lang1", TODAY, PROGRESS, api)
        assert result is False


# ── update_daily_max_word_number ──────────────────────────────────────────────

class TestUpdateDailyMaxWordNumber:
    @pytest.mark.asyncio
    async def test_updates_both_daily_and_first_finish(self):
        """max_word_number is written to both record types on every call."""
        api = make_api()
        await update_daily_max_word_number("u1", "lang1", TODAY, 450, api)
        api.update_daily_statistics.assert_called_once()
        api.update_daily_first_finish_statistics.assert_called_once()

    @pytest.mark.asyncio
    async def test_passes_max_word_number_in_payload(self):
        api = make_api()
        await update_daily_max_word_number("u1", "lang1", TODAY, 750, api)
        call_args = api.update_daily_statistics.call_args
        payload = call_args.args[3] if call_args.args else call_args.kwargs.get("stats_update", {})
        assert payload.get("max_word_number") == 750

    @pytest.mark.asyncio
    async def test_skips_when_word_number_is_zero(self):
        """word_number=0 means unknown — skip the update entirely."""
        api = make_api()
        await update_daily_max_word_number("u1", "lang1", TODAY, 0, api)
        api.update_daily_statistics.assert_not_called()
        api.update_daily_first_finish_statistics.assert_not_called()

    @pytest.mark.asyncio
    async def test_updates_on_every_call(self):
        """Unlike create_if_missing, max_word_number is sent on every word."""
        api = make_api()
        await update_daily_max_word_number("u1", "lang1", TODAY, 100, api)
        await update_daily_max_word_number("u1", "lang1", TODAY, 500, api)
        await update_daily_max_word_number("u1", "lang1", TODAY, 300, api)
        assert api.update_daily_statistics.call_count == 3


# ── update_daily_first_finish_statistics ──────────────────────────────────────

class TestUpdateDailyFirstFinishStatistics:
    @pytest.mark.asyncio
    async def test_always_overwrites(self):
        """Session completion always overwrites first_finish (no existence check)."""
        api = make_api(ff_exists=True)
        result = await update_daily_first_finish_statistics("u1", "lang1", TODAY, PROGRESS, api)
        assert result is True
        # PUT is called directly — no GET check
        api.get_daily_first_finish_statistics.assert_not_called()
        api.update_daily_first_finish_statistics.assert_called_once()

    @pytest.mark.asyncio
    async def test_returns_false_on_api_error(self):
        api = make_api()
        api.update_daily_first_finish_statistics.return_value = {"success": False, "error": "fail"}
        result = await update_daily_first_finish_statistics("u1", "lang1", TODAY, PROGRESS, api)
        assert result is False


# ── Integration: _bg_update_daily word_number flow ────────────────────────────

class TestBgUpdateDailyFlow:
    """Verifies that the full _bg_update_daily call sequence is correct."""

    @pytest.mark.asyncio
    async def test_daily_and_ff_seeded_and_max_updated_on_first_word_of_day(self):
        """
        When the first word of the day is rated:
        - daily record is created
        - first_finish record is seeded (if missing)
        - max_word_number is written
        All three things happen in one bg task.
        """
        api = make_api(daily_exists=False, ff_exists=False)
        api.get_user_progress = AsyncMock(return_value={"success": True, "result": PROGRESS})

        # import here to avoid circular at module level
        from app.services.statistics_service import (
            update_daily_statistics,
            create_first_finish_if_missing,
            update_daily_max_word_number,
        )

        progress = PROGRESS.copy()
        today = TODAY

        await update_daily_statistics("u1", "lang1", today, progress, api)
        await create_first_finish_if_missing("u1", "lang1", today, progress, api)
        await update_daily_max_word_number("u1", "lang1", today, 297, api)

        # daily created once
        api.update_daily_statistics.assert_called()
        # first_finish seeded once
        api.update_daily_first_finish_statistics.assert_called()
        # max_word_number 297 present in one of the calls
        max_wn_calls = [
            c for c in api.update_daily_statistics.call_args_list
            if (c.args[3] if c.args else {}).get("max_word_number") == 297
        ]
        assert len(max_wn_calls) == 1

    @pytest.mark.asyncio
    async def test_ff_not_overwritten_on_subsequent_words(self):
        """
        On words 2+ of the day:
        - update_daily_statistics does NOT call api.update_daily_statistics (record exists)
        - create_first_finish_if_missing does NOT call api.update_daily_first_finish_statistics (record exists)
        - update_daily_max_word_number DOES call both api methods (always runs)
        """
        api = make_api(daily_exists=True, ff_exists=True)

        await update_daily_statistics("u1", "lang1", TODAY, PROGRESS, api)
        # daily exists → no PUT call from update_daily_statistics itself
        # (update_daily_max_word_number hasn't run yet)
        api.update_daily_statistics.assert_not_called()

        await create_first_finish_if_missing("u1", "lang1", TODAY, PROGRESS, api)
        # ff exists → no PUT from create_if_missing
        api.update_daily_first_finish_statistics.assert_not_called()

        await update_daily_max_word_number("u1", "lang1", TODAY, 400, api)
        # max_word_number always fires both
        api.update_daily_statistics.assert_called_once()
        api.update_daily_first_finish_statistics.assert_called_once()
