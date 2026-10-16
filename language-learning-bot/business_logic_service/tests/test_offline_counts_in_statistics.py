"""
Первый финиш должен записываться — и офлайн, и онлайн.

Жалоба владельца: на графике «не знал на первом проходе» за месяц четыре точки.
После первой правки — по-прежнему четыре.

Две причины, одна за другой.

1. Ответы приходят двумя путями: по одному через /session/.../rate и пачкой
   через /results/batch, когда телефон догоняет накопленное офлайн. Путь пачки
   не писал ни дневной снимок, ни максимум номера, ни финиш — офлайновых
   занятий для статистики не существовало.

2. Сам признак финиша не наступал. Сначала им был конец партии сессии, но
   партия — сто слов (повторы плюс новые), а в день проходится 25–60: партия
   кончаться перестала. Потом я поставил «слов на сегодня больше нет» — а это
   не наступает в принципе: «не знаю» переносит срок на сегодня, слово
   возвращается в тот же день, и ноля не будет, пока человек не выучит всё.

Теперь признак из данных: порция — назначенные на сегодня повторы; первый
проход кончился, когда каждое слово порции показано хотя бы раз в этих сутках.
Как эти числа считает база — в backend/tests/test_repositories/
test_portion_first_pass.py.
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

    def __init__(self, portion_left: int = 0, answered_today: int = 1,
                 unknown: int = 0, has_record: bool = False,
                 words_for_today: int = 0):
        self.state = {
            "words_portion_left": portion_left,
            "words_answered_today": answered_today,
            "words_unknown_now": unknown,
        }
        # «Слов на сегодня» остаётся в прогрессе: по нему признак и был раньше,
        # и проверки показывают, что теперь он на признак не влияет.
        self.progress = {"words_for_today": words_for_today,
                         "words_unknown_now": unknown}
        self.has_record = has_record
        self.written: list = []

    async def get_portion_state(self, user_id, language_id):
        return {"success": True, "result": dict(self.state)}

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
async def test_the_finish_does_not_drag_the_heavy_progress(monkeypatch):
    """
    Признак спрашивается на каждый ответ, поэтому спрашивать его надо дёшево:
    в ответе прогресса — массивы номеров слов по записи на каждое изученное.
    Проверяем, что финиш за прогрессом не ходит вовсе.
    """
    async def forbidden(*a, **kw):
        raise AssertionError("финиш запросил тяжёлый прогресс")

    monkeypatch.setattr(svc, "get_user_progress", forbidden)
    api = _Api(portion_left=0, answered_today=12, unknown=4)
    assert await svc.write_first_finish_if_day_is_done("u1", "l1", api) is True
    assert api.written and api.written[0][1] == {"words_unknown": 4}


@pytest.mark.asyncio
async def test_the_finish_is_written_when_the_portion_is_done():
    """Порция была и пройдена вся — это и есть первый финиш."""
    api = _Api(portion_left=0, answered_today=40, unknown=7)
    assert await svc.write_first_finish_if_day_is_done("u1", "l1", api) is True
    assert len(api.written) == 1, api.written
    assert api.written[0][1] == {"words_unknown": 7}


@pytest.mark.asyncio
async def test_nothing_is_written_while_words_of_the_portion_are_left():
    """Пока слова порции не показаны, человек ещё идёт, и писать нечего."""
    api = _Api(portion_left=5, answered_today=12, unknown=7)
    assert await svc.write_first_finish_if_day_is_done("u1", "l1", api) is False
    assert api.written == []


@pytest.mark.asyncio
async def test_repeats_of_the_same_day_do_not_block_the_finish():
    """
    Сторож против прежнего условия. «Не знаю» возвращает слово в тот же день:
    слов «на сегодня» снова много, хотя порция пройдена. На старом условии
    («слов на сегодня нет») запись не делалась никогда — это и дало четыре
    точки на графике за месяц.
    """
    api = _Api(portion_left=0, answered_today=57, words_for_today=16, unknown=16)
    assert await svc.write_first_finish_if_day_is_done("u1", "l1", api) is True
    assert api.written and api.written[0][1] == {"words_unknown": 16}


@pytest.mark.asyncio
async def test_a_day_without_study_writes_nothing():
    """
    Человек сегодня не занимался — пустая порция тоже даёт ноль «осталось», и
    без этой оговорки запись легла бы в день, когда приложение не открывали.
    """
    api = _Api(portion_left=0, answered_today=0, unknown=3)
    assert await svc.write_first_finish_if_day_is_done("u1", "l1", api) is False
    assert api.written == []


@pytest.mark.asyncio
async def test_knowing_the_whole_portion_still_counts_as_a_finish():
    """
    Самый удачный день: все повторы отвечены «знаю». Слова уехали сроком в
    будущее, в порции их больше не видно — и запись всё равно обязана быть.
    """
    api = _Api(portion_left=0, answered_today=52, unknown=0)
    assert await svc.write_first_finish_if_day_is_done("u1", "l1", api) is True
    assert api.written and api.written[0][1] == {"words_unknown": 0}


@pytest.mark.asyncio
async def test_the_record_of_the_day_is_not_overwritten():
    """«Первый» значит первый: запись за день делается один раз."""
    api = _Api(portion_left=0, answered_today=30, unknown=3, has_record=True)
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
        "u1", "l1", Broken(answered_today=10)) is False


@pytest.mark.asyncio
async def test_an_old_backend_without_the_counters_writes_nothing():
    """
    Полей может не быть (бэкенд старее BLS при раскатке). Тогда молчим, а не
    пишем наугад: пропущенный день честнее выдуманного числа.
    """
    api = _Api()
    api.state = {"words_unknown_now": 5}
    assert await svc.write_first_finish_if_day_is_done("u1", "l1", api) is False
    assert api.written == []


@pytest.mark.asyncio
async def test_an_unreachable_backend_writes_nothing():
    """Ручка не ответила — молчим. Ноль в признаке нельзя принимать за финиш."""
    class _Down(_Api):
        async def get_portion_state(self, user_id, language_id):
            return {"success": False, "status": 500, "result": None}

    api = _Down(portion_left=0, answered_today=30)
    assert await svc.write_first_finish_if_day_is_done("u1", "l1", api) is False
    assert api.written == []


@pytest.mark.asyncio
async def test_both_paths_write_the_finish_through_one_place(monkeypatch):
    """
    Разводка: финиш зовётся из after_answers_applied, через которую проходят
    оба пути — и одиночные ответы, и пачка. Без этого остальные проверки
    бессильны: функция может быть верной и никем не вызванной.
    """
    called: list = []

    async def spy(user_id, language_id, api_client):
        called.append((user_id, language_id))
        return True

    monkeypatch.setattr(svc, "write_first_finish_if_day_is_done", spy)
    monkeypatch.setattr(svc, "update_daily_statistics",
                        lambda *a, **kw: _done())
    monkeypatch.setattr(svc, "study_day", lambda **kw: "2026-10-16")

    class _Settings:
        async def get_settings(self, *a, **kw):
            return {}

    class _Cache:
        def schedule_warm(self, *a, **kw):
            pass

    import app.services as services
    monkeypatch.setattr(services, "settings_service", _Settings(), raising=False)
    monkeypatch.setattr(services, "chart_cache", _Cache(), raising=False)

    await svc.after_answers_applied("u1", "l1", _Api())
    assert called == [("u1", "l1")], "первый финиш не зовётся после записи ответов"


async def _done():
    return None


def test_the_batch_route_schedules_the_statistics():
    """
    Ручка пачки обязана звать общую функцию в фоне — иначе офлайн снова выпадет
    из статистики, а телефон будет ждать пересчёта вместо подтверждения.
    """
    source = (ROOT / "app" / "routers" / "results.py").read_text(encoding="utf-8")
    assert "after_answers_applied" in source, "статистика после пачки не считается"
    assert "BackgroundTasks" in source, "статистика считается в ответе, задерживая телефон"
