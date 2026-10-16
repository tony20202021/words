"""
Кеш картинок статистики: перерисовка — только когда меняются данные.

Замер 18.09: экран статистики — 17 картинок, 6,5 с сервера на холодном кеше и
2,3 МБ по сети. Кеш жил 60 секунд, и графики, которые открывают изредка, почти
всегда рисовались заново, хотя их данные за день меняются два-три раза.
"""

import asyncio
import io
import time

import pytest
from PIL import Image

from app.services import chart_cache, statistics_service


@pytest.fixture(autouse=True)
def _clean():
    for store in (chart_cache._cache, chart_cache._current, chart_cache._locks,
                  chart_cache._viewed, chart_cache._pending):
        store.clear()
    yield


def _day(date, **fields):
    base = {"date": date, "words_studied": 100, "words_new": 0, "words_known": 99,
            "words_unknown_now": 1, "words_unknown_last_finish": 1,
            "words_overdue": 0, "words_for_today": 13,
            "max_word_number": 100, "updated_at": "2026-09-18T07:00:00"}
    base.update(fields)
    return base


def _stub(monkeypatch, days, first_finish=()):
    """Данные — из заглушки; отрисовка — счётчик вызовов, без matplotlib."""
    state = {"days": days, "ff": list(first_finish), "renders": 0}

    async def fake_stats(user_id, language_id, action_date, api_client, show_all=False):
        return state["days"], state["ff"]

    def fake_render(all_days, first_finish, show_all=False):
        state["renders"] += 1
        return {"words_studied": b"png"}

    monkeypatch.setattr(statistics_service, "get_monthly_statistics", fake_stats)
    monkeypatch.setattr(statistics_service, "generate_monthly_charts", fake_render)
    return state


@pytest.mark.asyncio
async def test_same_data_is_not_redrawn_however_long_it_waits(monkeypatch):
    """Прежде через 60 секунд всё рисовалось заново — теперь нет, пока данные те же."""
    state = _stub(monkeypatch, [_day("2026-09-17"), _day("2026-09-18")])
    await chart_cache.monthly_charts("u1", "l1", False, api_client=None)
    monkeypatch.setattr(time, "monotonic", lambda: 10 ** 9)   # «прошли годы»
    await chart_cache.monthly_charts("u1", "l1", False, api_client=None)
    assert state["renders"] == 1


@pytest.mark.asyncio
async def test_changed_data_is_redrawn(monkeypatch):
    state = _stub(monkeypatch, [_day("2026-09-18")])
    await chart_cache.monthly_charts("u1", "l1", False, api_client=None)
    state["days"] = [_day("2026-09-18", words_known=100)]
    await chart_cache.monthly_charts("u1", "l1", False, api_client=None)
    assert state["renders"] == 2


@pytest.mark.asyncio
async def test_fields_not_on_the_picture_do_not_reset_the_cache(monkeypatch):
    """
    max_word_number и время обновления меняются на каждом ответе. Учитывай их
    отпечаток — кеш сбрасывался бы от каждого слова и не значил бы ничего.
    """
    state = _stub(monkeypatch, [_day("2026-09-18")])
    await chart_cache.monthly_charts("u1", "l1", False, api_client=None)
    state["days"] = [_day("2026-09-18", max_word_number=205,
                          updated_at="2026-09-18T21:00:00")]
    await chart_cache.monthly_charts("u1", "l1", False, api_client=None)
    assert state["renders"] == 1


@pytest.mark.asyncio
async def test_first_finish_is_part_of_the_picture(monkeypatch):
    state = _stub(monkeypatch, [_day("2026-09-18")], [{"date": "2026-09-18", "words_unknown": 3}])
    await chart_cache.monthly_charts("u1", "l1", False, api_client=None)
    state["ff"] = [{"date": "2026-09-18", "words_unknown": 5}]
    await chart_cache.monthly_charts("u1", "l1", False, api_client=None)
    assert state["renders"] == 2


@pytest.mark.asyncio
async def test_simultaneous_requests_draw_once(monkeypatch):
    """Андроид теперь просит все картинки группы разом — рисоваться они должны один раз."""
    state = _stub(monkeypatch, [_day("2026-09-18")])
    await asyncio.gather(*[chart_cache.monthly_charts("u1", "l1", False, api_client=None)
                           for _ in range(7)])
    assert state["renders"] == 1


@pytest.mark.asyncio
async def test_old_pictures_of_the_same_chart_are_dropped(monkeypatch):
    state = _stub(monkeypatch, [_day("2026-09-18")])
    for known in range(5):
        state["days"] = [_day("2026-09-18", words_known=known)]
        await chart_cache.monthly_charts("u1", "l1", False, api_client=None)
    assert len(chart_cache._cache) == 1


# ── перерисовка заранее ──────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_warm_only_for_those_who_look_at_charts(monkeypatch):
    state = _stub(monkeypatch, [_day("2026-09-18")])
    monkeypatch.setattr(chart_cache, "WARM_DELAY_SECONDS", 0.01)
    chart_cache.schedule_warm("never-looked", "l1", api_client=None)
    await asyncio.sleep(0.05)
    assert state["renders"] == 0


@pytest.mark.asyncio
async def test_warm_waits_for_the_end_of_the_lesson(monkeypatch):
    """
    Каждый ответ отодвигает перерисовку: пока идёт учёба, процессор отдан
    карточкам. Серия ответов — одна перерисовка после последнего.
    """
    state = _stub(monkeypatch, [_day("2026-09-18")])
    monkeypatch.setattr(chart_cache, "WARM_DELAY_SECONDS", 0.05)
    chart_cache.note_view("u1", "l1")
    for _ in range(5):
        chart_cache.schedule_warm("u1", "l1", api_client=None)
        await asyncio.sleep(0.01)
    assert state["renders"] == 0, "пока идут ответы, рисовать рано"
    await asyncio.sleep(0.15)
    assert state["renders"] == 4, "после паузы — обе месячные группы в обоих вариантах, по разу"

    before = state["renders"]
    await chart_cache.monthly_charts("u1", "l1", False, api_client=None)
    assert state["renders"] == before, "открытие экрана после перерисовки — из кеша"


@pytest.mark.asyncio
async def test_viewers_are_forgotten_after_two_weeks(monkeypatch):
    state = _stub(monkeypatch, [_day("2026-09-18")])
    monkeypatch.setattr(chart_cache, "WARM_DELAY_SECONDS", 0.01)
    chart_cache._viewed[("u1", "l1")] = time.time() - chart_cache.VIEWERS_WINDOW_SECONDS - 1
    chart_cache.schedule_warm("u1", "l1", api_client=None)
    await asyncio.sleep(0.05)
    assert state["renders"] == 0


# ── сама картинка ────────────────────────────────────────────────────────────

def test_picture_fits_a_phone_and_is_a_palette_png():
    """
    Было 1770×1462 полноцветного PNG — втрое больше пикселей, чем показывает
    телефон; 17 картинок весили 2,3 МБ.
    """
    days = [{"date": f"2026-09-{d:02d}T00:00:00", "words_studied": 90 + d, "words_new": 1,
             "words_known": 80 + d, "words_unknown_now": d % 5, "words_overdue": 0,
             "words_unknown_last_finish": (d + 1) % 5,
             "words_for_today": 10 + d} for d in range(1, 18)]
    charts = statistics_service.generate_monthly_charts(days, [], show_all=True)
    image = Image.open(io.BytesIO(charts["words_studied"]))
    assert image.width <= 1100, image.size
    assert image.mode == "P", "полноцветный PNG вместо палитры"
    # Быстрое квантование сводит белый к (254,254,254) — фон должен остаться
    # тем же белым, что у экрана.
    assert image.convert("RGB").getpixel((0, 0)) == (255, 255, 255)


def test_every_monthly_chart_in_the_manifest_is_drawn():
    """Каждый график манифеста обязан рисоваться; лишних рисовать незачем."""
    from common.chart_manifest import MONTHLY_CHART_NAMES
    drawn = {name for _, name, _, _ in statistics_service.MONTHLY_SPECS}
    assert set(MONTHLY_CHART_NAMES) == drawn


# ── два варианта: для экрана и для увеличения ────────────────────────────────

def _real_days():
    return [{"date": f"2026-09-{d:02d}T00:00:00", "words_studied": 90 + d, "words_new": 1,
             "words_known": 80 + d, "words_unknown_now": d % 5, "words_overdue": 0,
             "words_unknown_last_finish": (d + 1) % 5,
             "words_for_today": 10 + d} for d in range(1, 18)]


def test_zoom_variant_is_sharper_than_screen():
    """
    Владелец увеличивает графики в вебе, и разрешения экрана там мало. Вариант
    для увеличения — прежние 300 dpi; экранный остаётся лёгким.
    """
    from app import chart_generator
    days = _real_days()
    screen = statistics_service.generate_monthly_charts(days, [], show_all=True)["words_studied"]
    with chart_generator.render_dpi(chart_generator.ZOOM_DPI):
        zoom = statistics_service.generate_monthly_charts(days, [], show_all=True)["words_studied"]
    ws = Image.open(io.BytesIO(screen)).width
    wz = Image.open(io.BytesIO(zoom)).width
    assert wz > ws * 1.5, (ws, wz)
    assert Image.open(io.BytesIO(zoom)).mode == "P", "и большой — в палитре"


def test_render_dpi_does_not_leak_into_the_next_drawing():
    from app import chart_generator
    days = _real_days()
    with chart_generator.render_dpi(chart_generator.ZOOM_DPI):
        statistics_service.generate_monthly_charts(days, [], show_all=True)
    after = statistics_service.generate_monthly_charts(days, [], show_all=True)["words_studied"]
    assert Image.open(io.BytesIO(after)).width <= 1100


@pytest.mark.asyncio
async def test_variants_are_cached_separately(monkeypatch):
    state = _stub(monkeypatch, [_day("2026-09-18")])
    await chart_cache.monthly_charts("u1", "l1", False, None, "screen")
    await chart_cache.monthly_charts("u1", "l1", False, None, "zoom")
    await chart_cache.monthly_charts("u1", "l1", False, None, "screen")
    await chart_cache.monthly_charts("u1", "l1", False, None, "zoom")
    assert state["renders"] == 2, "по одной отрисовке на вариант"


def test_unknown_variant_is_rejected():
    from fastapi.testclient import TestClient
    from app.main import app
    resp = TestClient(app).get("/statistics/u1/l1/monthly-chart/words_studied?res=huge")
    assert resp.status_code == 422


# ── версия данных: один короткий запрос вместо семнадцати картинок ───────────

class TestChartsVersion:
    """
    Жалоба владельца: в метро связь есть, но слабая, и графики грузятся
    мучительно. Телефон хранит картинки с прошлого раза, и по версии данных
    решает, качать ли свежие. Версия поэтому обязана меняться ровно тогда,
    когда изменилась бы картинка.
    """

    @staticmethod
    def _progress(monkeypatch, **fields):
        base = {"word_numbers_for_today": [1, 2], "word_numbers_unknown": [3],
                "word_check_interval": [1, 2], "words_studied": 100}
        base.update(fields)

        async def fake_progress(user_id, language_id, api_client):
            return base

        monkeypatch.setattr(statistics_service, "get_user_progress", fake_progress)
        return base

    @pytest.mark.asyncio
    async def test_the_same_data_gives_the_same_version(self, monkeypatch):
        _stub(monkeypatch, [_day("2026-09-01T00:00:00")])
        self._progress(monkeypatch)
        first = await chart_cache.charts_version("u1", "l1", api_client=None)
        second = await chart_cache.charts_version("u1", "l1", api_client=None)
        assert first == second and len(first) == 40

    @pytest.mark.asyncio
    async def test_a_new_answer_changes_the_version(self, monkeypatch):
        state = _stub(monkeypatch, [_day("2026-09-01T00:00:00")])
        self._progress(monkeypatch)
        before = await chart_cache.charts_version("u1", "l1", api_client=None)
        state["days"] = [_day("2026-09-01T00:00:00", words_studied=101)]
        assert await chart_cache.charts_version("u1", "l1", api_client=None) != before

    @pytest.mark.asyncio
    async def test_todays_charts_are_counted_too(self, monkeypatch):
        _stub(monkeypatch, [_day("2026-09-01T00:00:00")])
        self._progress(monkeypatch)
        before = await chart_cache.charts_version("u1", "l1", api_client=None)
        self._progress(monkeypatch, word_numbers_unknown=[3, 4])
        assert await chart_cache.charts_version("u1", "l1", api_client=None) != before

    @pytest.mark.asyncio
    async def test_a_new_release_changes_the_version(self, monkeypatch):
        """
        Картинка зависит не только от данных, но и от того, как её рисуют. В
        4.27.0 горизонтальная ось стала пропорциональной датам — данные при этом
        не менялись, и телефон показывал бы сохранённые картинки со старой осью
        до первой новой записи в статистике. На сервере это незаметно: его кеш
        живёт в памяти и умирает при перезапуске.
        """
        _stub(monkeypatch, [_day("2026-09-01T00:00:00")])
        self._progress(monkeypatch)
        before = await chart_cache.charts_version("u1", "l1", api_client=None)
        monkeypatch.setattr(chart_cache, "__version__", "99.99.99")
        assert await chart_cache.charts_version("u1", "l1", api_client=None) != before

    @pytest.mark.asyncio
    async def test_fields_not_on_the_picture_do_not_change_it(self, monkeypatch):
        """Иначе телефон качал бы всё заново из-за времени обновления записи."""
        state = _stub(monkeypatch, [_day("2026-09-01T00:00:00")])
        self._progress(monkeypatch)
        before = await chart_cache.charts_version("u1", "l1", api_client=None)
        state["days"] = [_day("2026-09-01T00:00:00", updated_at="2026-09-26T10:00:00",
                              max_word_number=500)]
        assert await chart_cache.charts_version("u1", "l1", api_client=None) == before


# ── отрисовка не должна падать на живых данных ──────────────────────────────

class TestIntervalHistogramSurvivesRealData:
    """
    График «Интервалы повторения» падал в бою: 63 раза за девять дней он не
    рисовался вовсе, и на экране оставалась вечная крутяшка.

    Насыщенность точки считалась как «сколько слов корзины имеют этот интервал,
    делить на ширину корзины». Это верно, пока слов в корзине не больше её
    ширины. В базе у одного слова оказалось несколько записей статистики
    (их наплодил разбор офлайн-пачки 30.09), и доля переваливала за единицу —
    matplotlib на такой прозрачности падает с ValueError.
    """

    @staticmethod
    def _draw(pairs):
        from app.chart_generator import ProgressChartGenerator
        return ProgressChartGenerator.create_check_interval_histogram(pairs, words_studied=200)

    def test_duplicate_records_for_one_word_do_not_break_the_picture(self):
        # Сорок записей на двадцать номеров одной корзины: доля была бы 2.0.
        pairs = [(100 + i % 20, 3) for i in range(40)]
        png = self._draw(pairs)
        assert png.getbuffer().nbytes > 0

    def test_a_normal_set_still_draws(self):
        pairs = [(i, i % 5) for i in range(1, 120)]
        assert self._draw(pairs).getbuffer().nbytes > 0

    def test_no_intervals_at_all_draws_the_explanation(self):
        assert self._draw([]).getbuffer().nbytes > 0
