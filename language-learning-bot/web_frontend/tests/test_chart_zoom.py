"""
Два варианта картинок статистики: лёгкий под экран и большой для увеличения.

Владелец увеличивает графики в вебе. После перехода на картинки под ширину
экрана их стало мало для увеличения; теперь страница показывает лёгкие сразу, а
большие подкачивает фоном и подменяет, не блокируя страницу.
"""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from tests.conftest import make_mock_bls


@pytest.fixture
def client():
    return TestClient(app)


def _login(client, bls):
    with patch("app.routers.auth.get_bls_client", return_value=bls):
        client.post("/login", data={"mode": "name", "name": "Test"}, follow_redirects=False)


@pytest.mark.parametrize("url,method,kwargs", [
    ("/stats/chart/lang1/check_interval", "get_chart", {}),
    ("/stats/monthly-chart/lang1/words_studied", "get_monthly_chart", {"show_all": True}),
    ("/stats/monthly-chart-recent/lang1/words_studied", "get_monthly_chart", {"show_all": False}),
])
@pytest.mark.parametrize("asked,sent", [("zoom", "zoom"), ("screen", "screen"),
                                        (None, "screen"), ("huge", "screen")])
def test_route_forwards_the_variant(client, url, method, kwargs, asked, sent):
    bls = make_mock_bls()
    _login(client, bls)
    setattr(bls, method, AsyncMock(return_value=b"png"))
    full = url + (f"?res={asked}" if asked else "")
    with patch("app.routers.info.get_bls_client", return_value=bls):
        resp = client.get(full)
    assert resp.status_code == 200
    call = getattr(bls, method).call_args
    assert call.kwargs.get("res") == sent, (full, call)
    for k, v in kwargs.items():
        assert call.kwargs.get(k) == v


def test_page_marks_every_chart_with_its_zoom_address(client):
    bls = make_mock_bls()
    _login(client, bls)
    bls.get_languages = AsyncMock(return_value=[{"id": "lang1", "name_ru": "Иврит", "name_foreign": "עברית"}])
    bls.get_statistics = AsyncMock(return_value={"words_for_today": 1, "words_studied": 5, "total_words": 10})
    with patch("app.routers.info.get_bls_client", return_value=bls):
        html = client.get("/stats").text
    lazy = html.count('class="img-fluid rounded lazy-chart"')
    zoom = html.count('?res=zoom"')
    assert lazy > 0 and zoom == lazy, f"картинок {lazy}, с адресом большого варианта {zoom}"
    assert "upgradeToZoom" in html and "pagehide" in html, "нет фоновой подмены или её обрыва"
