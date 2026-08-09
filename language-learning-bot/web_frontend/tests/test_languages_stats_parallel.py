"""
Список языков: статистика по всем языкам запрашивается разом, а не по одному.

/languages — первый экран после входа, и он собирал статистику циклом: по одному
HTTP-запросу к BLS на язык, каждый следующий после ответа предыдущего. На /stats
то же самое уже делалось через asyncio.gather. Тест не меряет время (это было бы
гадание), а считает, сколько запросов висит в воздухе одновременно: при
последовательном цикле их всегда ровно один.
"""

import asyncio

import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient

from app.main import app
from tests.conftest import make_mock_bls

LANGS = [{"id": f"lang{i}", "name_ru": f"Язык {i}", "name_foreign": f"L{i}"}
         for i in range(1, 9)]


class _ConcurrencyProbe:
    """Считает максимальное число одновременно выполняющихся вызовов."""

    def __init__(self):
        self.inflight = 0
        self.max_inflight = 0
        self.calls = 0

    async def get_statistics(self, user_id, language_id):
        self.calls += 1
        self.inflight += 1
        self.max_inflight = max(self.max_inflight, self.inflight)
        # Точка переключения: без неё корутина досчитает до конца, не отдав
        # управление, и параллельность будет неотличима от последовательной.
        await asyncio.sleep(0)
        self.inflight -= 1
        return {"words_for_today": 1, "words_studied": 1, "total_words": 10}


@pytest.fixture
def client():
    return TestClient(app, raise_server_exceptions=True)


def _login(client, bls):
    with patch("app.routers.auth.get_bls_client", return_value=bls):
        client.post("/login", data={"mode": "name", "name": "Test"}, follow_redirects=False)


@pytest.mark.parametrize("url,router", [
    ("/languages", "app.routers.languages"),
    ("/stats", "app.routers.info"),
])
def test_statistics_for_all_languages_is_fetched_in_parallel(client, url, router):
    bls = make_mock_bls()
    _login(client, bls)

    probe = _ConcurrencyProbe()
    bls.get_languages = _async_value(LANGS)
    bls.get_statistics = probe.get_statistics

    with patch(f"{router}.get_bls_client", return_value=bls):
        resp = client.get(url)

    assert resp.status_code == 200
    assert probe.calls == len(LANGS), "статистика должна запрашиваться по каждому языку"
    assert probe.max_inflight == len(LANGS), (
        f"запросы уходят по одному ({probe.max_inflight} в полёте) — "
        "на восьми языках это восемь последовательных обращений к BLS")


def test_languages_page_still_shows_every_language(client):
    """Параллельность не должна терять или путать языки."""
    bls = make_mock_bls()
    _login(client, bls)
    bls.get_languages = _async_value(LANGS)

    async def stats(user_id, language_id):
        return {"words_for_today": int(language_id[-1]), "words_studied": 0, "total_words": 0}

    bls.get_statistics = stats
    with patch("app.routers.languages.get_bls_client", return_value=bls):
        resp = client.get("/languages")

    assert resp.status_code == 200
    for lang in LANGS:
        assert lang["name_ru"] in resp.text


def test_helper_maps_each_language_to_its_own_stats():
    """Ответы gather приходят по порядку задач — соответствие не должно съехать."""
    from app.stats import fetch_stats_for_languages

    class _Bls:
        async def get_statistics(self, user_id, language_id):
            # Разная задержка: если бы helper полагался на порядок завершения,
            # а не на порядок задач, соответствие бы перепуталось.
            await asyncio.sleep(0.01 if language_id == "lang1" else 0)
            return {"total_words": int(language_id[-1])}

    result = asyncio.run(fetch_stats_for_languages(_Bls(), "u1", LANGS))
    assert result == {lang["id"]: {"total_words": int(lang["id"][-1])} for lang in LANGS}


def test_helper_without_languages_makes_no_calls():
    from app.stats import fetch_stats_for_languages

    class _Bls:
        async def get_statistics(self, user_id, language_id):  # pragma: no cover
            raise AssertionError("вызовов быть не должно")

    assert asyncio.run(fetch_stats_for_languages(_Bls(), "u1", [])) == {}


def _async_value(value):
    from unittest.mock import AsyncMock
    return AsyncMock(return_value=value)
