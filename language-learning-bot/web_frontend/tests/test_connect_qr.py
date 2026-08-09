"""
Подключение второго устройства: код, ссылка под QR и сам прокси QR.

Ссылку под QR собирают из base_url вручную, и она уже была сломана: rstrip('/')
снимал слэш, а обратно он не добавлялся — получалось «https://host:8444login?code=…»,
то есть QR вёл в никуда. Ошибка невидима на глаз (код рядом набирается руками) и
не ловится ничем, кроме теста на саму ссылку.
"""

import re
from urllib.parse import unquote

import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient

from app.main import app
from tests.conftest import make_mock_bls


@pytest.fixture
def client():
    return TestClient(app, raise_server_exceptions=True)


@pytest.fixture
def bls():
    b = make_mock_bls()
    b.mobile_create_token = AsyncMock(return_value={"code": "ABC123"})
    return b


def _login(client, bls):
    with patch("app.routers.auth.get_bls_client", return_value=bls):
        client.post("/login", data={"mode": "name", "name": "Test"}, follow_redirects=False)


def test_connect_shows_the_code_and_a_working_link(client, bls):
    _login(client, bls)
    with patch("app.routers.auth.get_bls_client", return_value=bls):
        resp = client.get("/connect")

    assert resp.status_code == 200
    assert "ABC123" in resp.text

    src = re.search(r'/qr\?url=([^"]+)', resp.text)
    assert src, "QR на странице не найден"
    connect_url = unquote(src.group(1))
    assert connect_url == f"{client.base_url}/login?code=ABC123", connect_url
    # Тот самый склеенный вид, который получался без слэша.
    assert "testserverlogin" not in resp.text


def test_connect_without_a_code_says_so_instead_of_a_dead_qr(client, bls):
    _login(client, bls)
    bls.mobile_create_token = AsyncMock(return_value={})
    with patch("app.routers.auth.get_bls_client", return_value=bls):
        resp = client.get("/connect")

    assert resp.status_code == 200
    assert "Не удалось создать код" in resp.text
    assert "/qr?url=" not in resp.text


def test_connect_requires_login(client):
    resp = client.get("/connect", follow_redirects=False)
    assert resp.status_code == 302
    assert "/login" in resp.headers["location"]


# ── Прокси QR ────────────────────────────────────────────────────────────────

class _FakeHttp:
    def __init__(self, status_code=200, content=b"\x89PNG\r\n\x1a\nfake"):
        self.status_code = status_code
        self.content = content
        self.requested = []

    def __call__(self, *a, **kw):
        return self

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False

    async def get(self, url, params=None, **kw):
        self.requested.append((url, params))
        return self


def test_qr_proxies_the_png_from_bls(client, monkeypatch):
    import httpx
    fake = _FakeHttp()
    monkeypatch.setattr(httpx, "AsyncClient", fake)

    resp = client.get("/qr", params={"url": "http://testserver/login?code=ABC123"})

    assert resp.status_code == 200
    assert resp.headers["content-type"] == "image/png"
    assert resp.content == b"\x89PNG\r\n\x1a\nfake"
    url, params = fake.requested[0]
    assert url.endswith("/qr")
    assert params == {"url": "http://testserver/login?code=ABC123"}


def test_qr_returns_404_when_bls_cannot_draw_it(client, monkeypatch):
    import httpx
    monkeypatch.setattr(httpx, "AsyncClient", _FakeHttp(status_code=500, content=b""))
    resp = client.get("/qr", params={"url": "http://testserver/login?code=X"})
    assert resp.status_code == 404
