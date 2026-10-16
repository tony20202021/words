"""
Офлайновые занятия должны попадать в статистику наравне с онлайновыми.

Жалоба владельца: на графике «не знал на первом проходе» за месяц всего четыре
точки. Оказалось, что последняя запись — от 20.09, и после неё ни одной.

Причина. Ответы приходят двумя путями: по одному через /session/.../rate и
пачкой через /results/batch, когда телефон догоняет накопленное офлайн.
Онлайн-путь писал дневной снимок, максимум пройденного номера, подогревал
графики и на конце дневной порции записывал «первый финиш». Путь пачки не делал
ничего из этого — для статистики занятий в метро просто не существовало.
"""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT.parent))

from app.services import statistics_service as svc  # noqa: E402


class _Api:
    """Поддельный клиент: помнит, о чём его спрашивали и что просили записать."""

    def __init__(self, words_for_today: int, unknown: int = 0, has_record: bool = False):
        self.progress = {"words_for_today": words_for_today, "words_unknown_now": unknown}
        self.has_record = has_record
        self.written: list = []

    async def get_daily_first_finish_statistics(self, user_id, language_id, day):
        return {"success": True, "status": 200 if self.has_record else 404,
                "result": {"words_unknown": 1} if self.has_record else None}

    async def update_daily_first_finish_statistics(self, user_id, language_id, day, payload):
        self.written.append((day, payload))
        return {"success": True}

    async def get_user_language_settings(self, user_id, language_id):
        return {"success": True, "result": {}}


@pytest.fixture(autouse=True)
def _progress(monkeypatch):
    """Прогресс берём из поддельного клиента, в сеть не ходим."""
    async def fake(user_id, language_id, api_client):
        return api_client.progress
    monkeypatch.setattr(svc, "get_user_progress", fake)


@pytest.mark.asyncio
async def test_the_finish_is_written_when_the_day_is_done_offline():
    """Слов на сегодня не осталось — значит, порция пройдена, это и есть финиш."""
    api = _Api(words_for_today=0, unknown=7)
    assert await svc.write_first_finish_if_day_is_done("u1", "l1", api) is True
    assert len(api.written) == 1, api.written
    assert api.written[0][1] == {"words_unknown": 7}


@pytest.mark.asyncio
async def test_nothing_is_written_while_words_are_left():
    """
    Финиш — это конец дневной порции, а не любая отправка пачки. Пока слова на
    сегодня есть, человек ещё идёт, и писать нечего.
    """
    api = _Api(words_for_today=5, unknown=7)
    assert await svc.write_first_finish_if_day_is_done("u1", "l1", api) is False
    assert api.written == []


@pytest.mark.asyncio
async def test_the_record_of_the_day_is_not_overwritten():
    """
    «Первый» значит первый: запись за день делается один раз. Вторая отправка
    пачки в тот же день не должна затирать её более поздним числом.
    """
    api = _Api(words_for_today=0, unknown=3, has_record=True)
    assert await svc.write_first_finish_if_day_is_done("u1", "l1", api) is True
    assert api.written == [], "запись за день переписана"


@pytest.mark.asyncio
async def test_a_broken_client_does_not_break_the_batch():
    """
    Статистика — дело фоновое. Если она не вышла, ответы человека всё равно
    записаны, и отправка пачки не должна падать из-за неё.
    """
    class Broken(_Api):
        async def get_daily_first_finish_statistics(self, *a, **kw):
            raise RuntimeError("сеть")

    assert await svc.write_first_finish_if_day_is_done(
        "u1", "l1", Broken(words_for_today=0)) is False


def test_the_batch_route_asks_for_both_records():
    """
    Сама ручка пачки обязана звать оба действия — иначе офлайн снова выпадет
    из статистики. Проверяем разводку: без неё остальные проверки бессильны.
    """
    source = (ROOT / "app" / "routers" / "results.py").read_text(encoding="utf-8")
    assert "after_answers_applied" in source, "дневной снимок после пачки не пишется"
    assert "write_first_finish_if_day_is_done" in source, "первый финиш после пачки не пишется"
    assert "BackgroundTasks" in source, "статистика считается в ответе, задерживая телефон"
