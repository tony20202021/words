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
            "words_unknown_now": 1, "words_overdue": 0, "words_for_today": 13,
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
    assert state["renders"] == 2, "после паузы — обе месячные группы, один раз"

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
