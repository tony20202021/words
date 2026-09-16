"""
Unit tests for statistics_service — no I/O, no DB, pure logic with mocked api_client.

Covers:
- update_daily_statistics: create-if-missing snapshot
- update_daily_max_word_number: updates only daily record
- write_first_finish_if_missing: одна запись за сутки, не перезапись
- study_day: граница суток по Гринвичу
- «новых слов в день»: разница относится к более раннему дню
"""

import pytest
from datetime import date, datetime, timedelta
from unittest.mock import AsyncMock, call

from app.services.statistics_service import (
    update_daily_statistics,
    update_daily_max_word_number,
    write_first_finish_if_missing,
    study_day,
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


def make_api(*, daily_exists=False, finish_exists=None):
    """Return a mock api_client for statistics operations."""
    api = AsyncMock()
    api.get_daily_statistics.return_value = {
        "success": True,
        "result": {"words_studied": 100} if daily_exists else None,
    }
    api.update_daily_statistics.return_value = {"success": True, "result": {}}
    api.update_daily_first_finish_statistics.return_value = {"success": True, "result": {}}
    api.get_daily_first_finish_statistics.return_value = (
        {"success": True, "status": 200, "result": finish_exists} if finish_exists is not None
        else {"success": True, "status": 404, "result": None}
    )
    return api


def _finish_payload(api):
    call = api.update_daily_first_finish_statistics.call_args
    return call.args[3] if len(call.args) > 3 else call.kwargs.get("stats_update", {})


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


# ── write_first_finish_if_missing ─────────────────────────────────────────────

class TestFirstFinishWrite:
    """
    «Первый финиш за день»: сколько слов человек не знал, впервые за сутки дойдя
    до конца дневной порции. Ключевое слово — впервые: за день порция кончается
    много раз, и записать надо самый первый результат, пока он не улучшен
    повторениями. Поэтому запись идёт только при отсутствии записи за эти сутки.
    """

    @pytest.mark.asyncio
    async def test_writes_when_there_is_no_record_for_the_day(self):
        api = make_api()
        assert await write_first_finish_if_missing("u1", "lang1", TODAY, 7, api) is True
        api.update_daily_first_finish_statistics.assert_called_once()
        assert _finish_payload(api) == {"words_unknown": 7}

    @pytest.mark.asyncio
    async def test_keeps_the_first_value_of_the_day(self):
        """Второй финиш за те же сутки не трогает записанное — даже если стало лучше."""
        api = make_api(finish_exists={"words_unknown": 9})
        assert await write_first_finish_if_missing("u1", "lang1", TODAY, 3, api) is True
        api.update_daily_first_finish_statistics.assert_not_called()

    @pytest.mark.asyncio
    async def test_zero_is_a_value_and_gets_written(self):
        """
        Ноль законен: порция пройдена без ошибок. Прежний код в этом случае не
        писал ничего (он срабатывал только на «не знаю»), и такой день выпадал из
        графика вовсе — а это как раз лучший день.
        """
        api = make_api()
        await write_first_finish_if_missing("u1", "lang1", TODAY, 0, api)
        api.update_daily_first_finish_statistics.assert_called_once()
        assert _finish_payload(api) == {"words_unknown": 0}

    @pytest.mark.asyncio
    async def test_missing_record_reported_as_404_result_none(self):
        """Бэкенд отвечает на отсутствие записи по-разному — оба ответа значат «нет»."""
        api = make_api()
        api.get_daily_first_finish_statistics.return_value = {
            "success": False, "status": 404, "result": None}
        await write_first_finish_if_missing("u1", "lang1", TODAY, 2, api)
        api.update_daily_first_finish_statistics.assert_called_once()

    @pytest.mark.asyncio
    async def test_returns_false_when_write_fails(self):
        api = make_api()
        api.update_daily_first_finish_statistics.return_value = {
            "success": False, "error": "fail"}
        assert await write_first_finish_if_missing("u1", "lang1", TODAY, 5, api) is False


# ── study_day ─────────────────────────────────────────────────────────────────

class TestStudyDay:
    """
    Занятие после полуночи по Москве — это ещё вчерашний день учёбы: набор слов
    вчерашний, сессия вчерашняя. Граница проведена по Гринвичу, то есть в 3 часа
    ночи по Москве — между занятиями, а не посреди них.
    """

    def _moscow(self, hour, minute=0, day=16):
        """Московское время → наивный UTC, каким его видит сервер."""
        return datetime(2026, 9, day, hour, minute) - timedelta(hours=3)

    def test_after_midnight_moscow_still_belongs_to_the_previous_day(self):
        assert study_day(self._moscow(1, 30)) == date(2026, 9, 15)

    def test_night_owl_session_at_two_fifty_nine_is_previous_day(self):
        assert study_day(self._moscow(2, 59)) == date(2026, 9, 15)

    def test_early_morning_starts_the_new_day(self):
        assert study_day(self._moscow(4)) == date(2026, 9, 16)

    def test_daytime_is_its_own_date(self):
        assert study_day(self._moscow(14)) == date(2026, 9, 16)

    def test_defaults_to_current_time(self):
        assert study_day() == datetime.utcnow().date()




# ── месячная статистика: путь «данных нет» ────────────────────────────────────

class TestMonthlyStatisticsWithoutData:
    """
    У нового пользователя месячной статистики ещё нет. Этот путь не проверял
    никто — и когда функция стала возвращать две величины вместо трёх, пустой
    возврат остался тройным. Весь набор тестов при этом оставался зелёным, а
    экран графиков у такого пользователя упал бы на распаковке.
    """

    @pytest.mark.asyncio
    async def test_returns_as_many_values_as_callers_unpack(self):
        from app.services.statistics_service import get_monthly_statistics
        api = AsyncMock()
        api.get_monthly_statistics.return_value = {
            "success": True, "status": 404, "result": None}
        all_days, first_finish = await get_monthly_statistics("u1", "lang1", TODAY, api)
        assert all_days == []
        assert first_finish == []

    @pytest.mark.asyncio
    async def test_failed_request_also_unpacks(self):
        from app.services.statistics_service import get_monthly_statistics
        api = AsyncMock()
        api.get_monthly_statistics.return_value = {
            "success": False, "status": 500, "result": None, "error": "boom"}
        all_days, first_finish = await get_monthly_statistics("u1", "lang1", TODAY, api)
        assert (all_days, first_finish) == ([], [])

    def test_no_days_means_no_charts(self):
        from app.services.statistics_service import generate_monthly_charts
        assert generate_monthly_charts([], []) == {}


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


# ── «Новых слов в день»: к какому дню относить разницу снимков ────────────────

def _monthly_api(studied_by_day, morning=None):
    """Клиент, отдающий дневные снимки в порядке дат, как их отдаёт бэкенд."""
    days = []
    for i, st in enumerate(studied_by_day):
        day = {"date": f"2026-08-{13 + i:02d}T00:00:00", "words_studied": st,
               "words_known": st, "words_skipped": 0}
        if morning:
            day.update(morning[i])
        days.append(day)
    api = AsyncMock()
    api.get_monthly_statistics.return_value = {
        "success": True, "status": 200, "result": {"daily_stats": days}}
    api.get_monthly_first_finish_statistics.return_value = {
        "success": True, "status": 200, "result": {"daily_stats": []}}
    return api


async def _new_words(studied_by_day):
    from app.services.statistics_service import get_monthly_statistics
    all_days, _ = await get_monthly_statistics(
        "u1", "l1", date(2026, 8, 20), _monthly_api(studied_by_day), show_all=False)
    return [d["words_new"] for d in all_days]


class TestNewWordsPerDay:
    """
    Снимок «изучено» пишется один раз — на первом ответе дня, до занятий. Значит
    снимок дня D равен итогу дня D−1, и разница соседних снимков — это слова,
    выученные в более РАННИЙ из двух дней.
    """

    @pytest.mark.asyncio
    async def test_the_owners_case_zero_stays_on_the_day_without_new_words(self):
        """
        13.08 новых слов не было, 14.08 выучено пять. Утренние снимки: 51, 51, 56.
        Раньше график ставил ноль на 14.08 — ровно в день, где новые были, — и
        пятёрку на 15.08.
        """
        assert await _new_words([51, 51, 56]) == [0, 5, None]

    @pytest.mark.asyncio
    async def test_every_delta_lands_one_day_earlier_than_before(self):
        # Прежний расчёт дал бы [None, 0, 2, 5] — тот же ряд, сдвинутый на сутки.
        assert await _new_words([5, 5, 7, 12]) == [0, 2, 5, None]

    @pytest.mark.asyncio
    async def test_the_last_day_has_no_point_until_the_next_snapshot(self):
        """Итог сегодняшнего дня появится с завтрашним первым ответом, не раньше."""
        result = await _new_words([10, 12])
        assert result[-1] is None

    @pytest.mark.asyncio
    async def test_a_drop_in_studied_is_not_shown_as_negative_new_words(self):
        assert await _new_words([10, 8, 9]) == [None, 1, None]

    @pytest.mark.asyncio
    async def test_morning_counters_pass_through_untouched(self):
        """
        Сдвиг касается только «новых слов». Утренние счётчики недоученного
        приходят из дневной записи как есть — сервис их не пересчитывает.

        Прежде здесь считалось «неизвестных до завершения» как
        studied − known − skipped. Эта величина смешивала оставшиеся «не знаю» с
        недопройденными и после законченного дня всегда давала ноль; вместо неё
        бэкенд пишет два раздельных счётчика.
        """
        from app.services.statistics_service import get_monthly_statistics
        api = _monthly_api([100, 100], morning=[
            {"words_unknown_now": 3, "words_overdue": 2},
            {"words_unknown_now": 0, "words_overdue": 0},
        ])
        all_days, _ = await get_monthly_statistics(
            "u1", "l1", date(2026, 8, 20), api, show_all=False)
        assert [(d["words_unknown_now"], d["words_overdue"]) for d in all_days] == [(3, 2), (0, 0)]
        # Старого сводного поля больше нет — чтобы никто не строил по нему график.
        assert "words_unknown" not in all_days[0]


# ── первый финиш за день и граница учебных суток ──────────────────────────────

class TestFirstFinishOnce:
    """
    «Первый финиш» — сколько слов человек не знал, впервые дойдя до конца дневной
    порции. Набор слов каждый день почти новый, поэтому число сравнимо изо дня в
    день.

    С 10 июня по 16 сентября здесь писался счётчик ошибок сессии на КАЖДОЕ
    «не знаю»: он считал ответы, а не слова, и обнулялся при каждом новом сеансе,
    а сессия за день начинается заново от двух до десяти раз.
    """

    def _api(self, exists: bool):
        api = AsyncMock()
        api.get_daily_first_finish_statistics.return_value = (
            {"success": True, "status": 200, "result": {"words_unknown": 5}} if exists
            else {"success": True, "status": 404, "result": None})
        api.update_daily_first_finish_statistics.return_value = {"success": True, "result": {}}
        return api

    @pytest.mark.asyncio
    async def test_writes_when_no_record_yet(self):
        api = self._api(exists=False)
        assert await write_first_finish_if_missing("u1", "l1", TODAY, 7, api) is True
        api.update_daily_first_finish_statistics.assert_called_once()
        payload = api.update_daily_first_finish_statistics.call_args.args[3]
        assert payload == {"words_unknown": 7}

    @pytest.mark.asyncio
    async def test_second_completion_of_the_day_changes_nothing(self):
        """Именно ПЕРВЫЙ финиш: повторные завершения порции запись не трогают."""
        api = self._api(exists=True)
        assert await write_first_finish_if_missing("u1", "l1", TODAY, 2, api) is True
        api.update_daily_first_finish_statistics.assert_not_called()

    @pytest.mark.asyncio
    async def test_reports_failure(self):
        api = self._api(exists=False)
        api.update_daily_first_finish_statistics.return_value = {"success": False, "error": "fail"}
        assert await write_first_finish_if_missing("u1", "l1", TODAY, 1, api) is False


class TestStudyDay:
    """
    Учебные сутки меняются в полночь по Гринвичу — по Москве это 3 часа ночи.
    Занятие после полуночи по местному времени остаётся вчерашней сессией.
    """

    def test_after_local_midnight_is_still_the_previous_day(self):
        from datetime import datetime as dt
        # 00:30 по Москве = 21:30 UTC предыдущих суток.
        assert study_day(dt(2026, 9, 14, 21, 30)) == date(2026, 9, 14)

    def test_morning_starts_the_new_day(self):
        from datetime import datetime as dt
        # 07:00 по Москве = 04:00 UTC.
        assert study_day(dt(2026, 9, 15, 4, 0)) == date(2026, 9, 15)

    def test_boundary_is_utc_midnight(self):
        from datetime import datetime as dt
        assert study_day(dt(2026, 9, 14, 23, 59)) == date(2026, 9, 14)
        assert study_day(dt(2026, 9, 15, 0, 1)) == date(2026, 9, 15)
