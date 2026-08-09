"""
Unit tests for statistics_service — no I/O, no DB, pure logic with mocked api_client.

Covers:
- update_daily_statistics: create-if-missing snapshot
- update_daily_max_word_number: updates only daily record
- update_daily_first_finish_statistics: backend decides whether to update (max-unknown guard)
- update_daily_last_finish_statistics: always overwrites
- _bg_update_daily / _bg_update_finish_on_unknown separation
"""

import pytest
from datetime import date
from unittest.mock import AsyncMock, call

from app.services.statistics_service import (
    update_daily_statistics,
    update_daily_max_word_number,
    update_daily_first_finish_statistics,
    update_daily_last_finish_statistics,
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


def make_api(*, daily_exists=False):
    """Return a mock api_client for statistics operations."""
    api = AsyncMock()
    api.get_daily_statistics.return_value = {
        "success": True,
        "result": {"words_studied": 100} if daily_exists else None,
    }
    api.update_daily_statistics.return_value = {"success": True, "result": {}}
    api.update_daily_first_finish_statistics.return_value = {"success": True, "result": {}}
    api.update_daily_last_finish_statistics.return_value = {"success": True, "result": {}}
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


# ── update_daily_max_word_number ──────────────────────────────────────────────

class TestUpdateDailyMaxWordNumber:
    @pytest.mark.asyncio
    async def test_updates_only_daily_record(self):
        """max_word_number is written to daily record only — not to first_finish."""
        api = make_api()
        await update_daily_max_word_number("u1", "lang1", TODAY, 450, api)
        api.update_daily_statistics.assert_called_once()
        api.update_daily_first_finish_statistics.assert_not_called()

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

    @pytest.mark.asyncio
    async def test_updates_on_every_call(self):
        """max_word_number is sent on every word — backend uses $max."""
        api = make_api()
        await update_daily_max_word_number("u1", "lang1", TODAY, 100, api)
        await update_daily_max_word_number("u1", "lang1", TODAY, 500, api)
        await update_daily_max_word_number("u1", "lang1", TODAY, 300, api)
        assert api.update_daily_statistics.call_count == 3


# ── update_daily_first_finish_statistics ──────────────────────────────────────

class TestUpdateDailyFirstFinishStatistics:
    @pytest.mark.asyncio
    async def test_calls_api_without_get_check(self):
        """Calls PUT directly — no GET check (backend performs max-unknown comparison)."""
        api = make_api()
        result = await update_daily_first_finish_statistics("u1", "lang1", TODAY, PROGRESS, api)
        assert result is True
        api.get_daily_statistics.assert_not_called()
        api.update_daily_first_finish_statistics.assert_called_once()

    @pytest.mark.asyncio
    async def test_passes_incorrect_count_as_words_unknown(self):
        """incorrect_count is sent as words_unknown — field name matches semantic meaning."""
        api = make_api()
        progress = {"words_unknown": 7}  # incorrect_count=7
        await update_daily_first_finish_statistics("u1", "lang1", TODAY, progress, api)
        call_args = api.update_daily_first_finish_statistics.call_args
        payload = call_args.args[3] if len(call_args.args) > 3 else call_args.kwargs.get("stats_update", {})
        assert payload.get("words_unknown") == 7

    @pytest.mark.asyncio
    async def test_returns_false_on_api_error(self):
        api = make_api()
        api.update_daily_first_finish_statistics.return_value = {"success": False, "error": "fail"}
        result = await update_daily_first_finish_statistics("u1", "lang1", TODAY, PROGRESS, api)
        assert result is False

    @pytest.mark.asyncio
    async def test_called_on_every_dont_know(self):
        """Called on every 'don't know' answer — backend skips when unknown did not increase."""
        api = make_api()
        for _ in range(5):
            await update_daily_first_finish_statistics("u1", "lang1", TODAY, PROGRESS, api)
        assert api.update_daily_first_finish_statistics.call_count == 5


# ── update_daily_last_finish_statistics ───────────────────────────────────────

class TestUpdateDailyLastFinishStatistics:
    @pytest.mark.asyncio
    async def test_calls_api_unconditionally(self):
        """Always overwrites regardless of current vs stored unknown."""
        api = make_api()
        result = await update_daily_last_finish_statistics("u1", "lang1", TODAY, PROGRESS, api)
        assert result is True
        api.update_daily_last_finish_statistics.assert_called_once()

    @pytest.mark.asyncio
    async def test_returns_false_on_api_error(self):
        api = make_api()
        api.update_daily_last_finish_statistics.return_value = {"success": False, "error": "fail"}
        result = await update_daily_last_finish_statistics("u1", "lang1", TODAY, PROGRESS, api)
        assert result is False

    @pytest.mark.asyncio
    async def test_called_on_every_dont_know(self):
        api = make_api()
        for _ in range(3):
            await update_daily_last_finish_statistics("u1", "lang1", TODAY, PROGRESS, api)
        assert api.update_daily_last_finish_statistics.call_count == 3


# ── Separation: _bg_update_daily vs _bg_update_finish_on_unknown ──────────────

class TestBgTaskSeparation:
    """
    _bg_update_daily  fires on every word rating (know/skip/dont_know):
      → update_daily_statistics + update_daily_max_word_number

    _bg_update_finish_on_unknown  fires only on 'don't know' (show_answer):
      → update_daily_first_finish_statistics + update_daily_last_finish_statistics
    """

    @pytest.mark.asyncio
    async def test_bg_update_daily_does_not_touch_first_or_last_finish(self):
        """Simulates _bg_update_daily: only daily and max_word_number are written."""
        api = make_api(daily_exists=False)

        await update_daily_statistics("u1", "lang1", TODAY, PROGRESS, api)
        await update_daily_max_word_number("u1", "lang1", TODAY, 300, api)

        api.update_daily_statistics.assert_called()
        api.update_daily_first_finish_statistics.assert_not_called()
        api.update_daily_last_finish_statistics.assert_not_called()

    @pytest.mark.asyncio
    async def test_bg_update_finish_writes_both_finish_records(self):
        """Simulates _bg_update_finish_on_unknown: both finish types are written with words_unknown."""
        api = make_api()
        progress = {"words_unknown": 5}  # incorrect_count=5 passed as words_unknown

        await update_daily_first_finish_statistics("u1", "lang1", TODAY, progress, api)
        await update_daily_last_finish_statistics("u1", "lang1", TODAY, progress, api)

        api.update_daily_first_finish_statistics.assert_called_once()
        api.update_daily_last_finish_statistics.assert_called_once()

    @pytest.mark.asyncio
    async def test_bg_update_finish_does_not_call_get_user_progress(self):
        """_bg_update_finish_on_unknown uses session incorrect_count directly — no DB fetch."""
        api = make_api()
        progress = {"words_unknown": 5}

        await update_daily_first_finish_statistics("u1", "lang1", TODAY, progress, api)
        await update_daily_last_finish_statistics("u1", "lang1", TODAY, progress, api)

        api.get_daily_statistics.assert_not_called()

    @pytest.mark.asyncio
    async def test_finish_records_not_updated_on_know_or_skip(self):
        """On 'know' or 'skip', finish records must not be touched."""
        api = make_api(daily_exists=True)

        # Simulate two 'know' words and one 'skip' word — only bg_update_daily fires
        for _ in range(3):
            await update_daily_statistics("u1", "lang1", TODAY, PROGRESS, api)
            await update_daily_max_word_number("u1", "lang1", TODAY, 100, api)

        api.update_daily_first_finish_statistics.assert_not_called()
        api.update_daily_last_finish_statistics.assert_not_called()

    @pytest.mark.asyncio
    async def test_finish_records_updated_on_each_dont_know(self):
        """On 3 'don't know' answers, finish stats are updated 3 times."""
        api = make_api()

        for _ in range(3):
            await update_daily_first_finish_statistics("u1", "lang1", TODAY, PROGRESS, api)
            await update_daily_last_finish_statistics("u1", "lang1", TODAY, PROGRESS, api)

        assert api.update_daily_first_finish_statistics.call_count == 3
        assert api.update_daily_last_finish_statistics.call_count == 3


# ── ленивая загрузка прогресса ────────────────────────────────────────────────

class TestLazyProgress:
    """
    Снимок прогресса нужен только при создании дневной записи — то есть раз в
    сутки. Раньше _bg_update_daily тянул полный прогресс на каждое оценённое
    слово, а он тяжёлый: word_numbers_for_today / word_numbers_unknown /
    word_check_interval — массивы на тысячи чисел, которые тут же выбрасывались.
    """

    @staticmethod
    def _loader(calls):
        async def load():
            calls.append(1)
            return PROGRESS
        return load

    @pytest.mark.asyncio
    async def test_loader_is_not_called_when_record_exists(self):
        api = make_api(daily_exists=True)
        calls = []
        assert await update_daily_statistics(
            "u1", "lang1", TODAY, self._loader(calls), api) is True
        assert calls == []
        api.update_daily_statistics.assert_not_called()

    @pytest.mark.asyncio
    async def test_loader_is_called_once_when_record_is_missing(self):
        api = make_api(daily_exists=False)
        calls = []
        assert await update_daily_statistics(
            "u1", "lang1", TODAY, self._loader(calls), api) is True
        assert calls == [1]
        payload = api.update_daily_statistics.call_args.args[3]
        assert payload == PROGRESS

    @pytest.mark.asyncio
    async def test_plain_dict_still_works(self):
        api = make_api(daily_exists=False)
        assert await update_daily_statistics("u1", "lang1", TODAY, PROGRESS, api) is True
        assert api.update_daily_statistics.call_args.args[3] == PROGRESS


class TestBgUpdateDaily:
    """Проверяем сам фоновый обработчик роутера, а не только сервис под ним."""

    @staticmethod
    def _api(daily_exists):
        api = make_api(daily_exists=daily_exists)
        api.get_user_progress.return_value = {"success": True, "result": PROGRESS}
        return api

    @pytest.mark.asyncio
    async def test_does_not_fetch_progress_when_daily_record_exists(self):
        from app.routers.session import _bg_update_daily
        api = self._api(daily_exists=True)
        await _bg_update_daily("u1", "lang1", api, 450)
        api.get_user_progress.assert_not_called()
        # единственная запись — max_word_number
        assert api.update_daily_statistics.call_count == 1
        assert api.update_daily_statistics.call_args.args[3] == {"max_word_number": 450}

    @pytest.mark.asyncio
    async def test_fetches_progress_when_daily_record_is_missing(self):
        from app.routers.session import _bg_update_daily
        api = self._api(daily_exists=False)
        await _bg_update_daily("u1", "lang1", api, 450)
        api.get_user_progress.assert_called_once_with("u1", "lang1")
        assert api.update_daily_statistics.call_count == 2
