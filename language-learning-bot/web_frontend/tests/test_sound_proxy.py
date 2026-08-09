"""
Прокси звука: обход каталога закрыт.

Ручка /sound/{path} намеренно доступна без сессии — звук тянут все три клиента,
в том числе офлайновый андроид, который кеширует файлы заранее. Из-за этого она
же была самым дешёвым способом прочитать чужой файл: закодированные ../
переживали quote здесь и unquote на стороне backend, а тот склеивал путь через
os.path.join без нормализации.

Проверка на стороне backend есть отдельно (realpath внутри базового каталога);
эта — чтобы запрос не уходил дальше веба вовсе.
"""

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(monkeypatch):
    from app.main import app
    return TestClient(app)


@pytest.mark.parametrize("path", [
    "%2e%2e%2f%2e%2e%2fetc%2fsecret.mp3",
    "%2E%2E/%2E%2E/etc/secret.mp3",
    "sub/%2e%2e/%2e%2e/etc/secret.mp3",
])
def test_encoded_traversal_is_refused(client, path):
    """Именно закодированный вид и был рабочим вектором: он доживал до обработчика."""
    r = client.get(f"/sound/{path}", follow_redirects=False)
    assert r.status_code == 400, r.text


@pytest.mark.parametrize("path", ["../../etc/secret.mp3", "a/../../b.mp3"])
def test_literal_traversal_never_reaches_the_handler(client, path):
    """
    Незакодированные ../ схлопывает сам HTTP-слой ещё до маршрутизации, так что
    до обработчика они не доходят и дают 404, а не 400. Проверка в обработчике —
    второй рубеж, а не единственный: нормализация зависит от транспорта, и
    полагаться на неё нельзя.
    """
    r = client.get(f"/sound/{path}", follow_redirects=False)
    assert r.status_code in (400, 404), r.text
    assert r.status_code != 200


def test_ordinary_path_is_not_refused_by_the_guard(client, monkeypatch):
    """Защита не должна ломать обычные пути: до backend запрос дойти обязан."""
    import app.routers.study as study

    class _Resp:
        is_success = True
        content = b"MP3"

    class _Client:
        async def __aenter__(self): return self
        async def __aexit__(self, *a): return False
        async def get(self, url, timeout=None): return _Resp()

    monkeypatch.setattr(study.httpx, "AsyncClient", lambda *a, **k: _Client())
    r = client.get("/sound/hebrew/0001.mp3")
    assert r.status_code == 200
    assert r.content == b"MP3"
