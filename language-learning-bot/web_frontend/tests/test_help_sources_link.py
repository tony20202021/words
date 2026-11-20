"""Ссылка на источники данных в веб-справке нажимается.

Справка показывается в <pre>, и адрес в ней был бы просто текстом: его
пришлось бы выделять и копировать. Лицензии (CC BY-SA 4.0 у Викисловаря,
wordfreq и FrequencyWords) просят именно ссылку на сведения об источниках.
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch

from app.main import app
from common.help_text import DATA_SOURCES_URL
from tests.conftest import make_mock_bls


@pytest.fixture
def client():
    return TestClient(app)


def test_help_page_links_to_the_data_sources(client):
    bls = make_mock_bls()
    with patch("app.routers.auth.get_bls_client", return_value=bls):
        client.post("/login", data={"mode": "name", "name": "Test"}, follow_redirects=False)
    html = client.get("/help").text
    assert f'href="{DATA_SOURCES_URL}"' in html, "адрес источников в справке не ссылка"
    assert 'target="_blank"' in html, "ссылка на GitHub уводит со справки в той же вкладке"
