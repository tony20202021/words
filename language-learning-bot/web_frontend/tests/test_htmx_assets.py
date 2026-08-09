"""
Подключение скриптов: htmx локально, скрипт карточки — вне свопаемого фрагмента.

Две вещи, которые ломались молча.

1. Скрипт карточки лежал в partials/word_card.html, то есть внутри области,
   которую HTMX подменяет целиком (hx-target="#word-area", hx-swap="outerHTML").
   Скрипт из свопнутого фрагмента браузер выполняет заново, и каждый ответ
   сервера навешивал ещё три обработчика на document (htmx:afterSwap,
   htmx:responseError, htmx:sendError). Снятия не было: за сессию в 50 слов их
   набиралось полторы сотни, и одна сетевая ошибка запускала
   window.location.reload() десятки раз подряд.

2. htmx тянулся с unpkg.com, тогда как bootstrap лежит в static/vendor. Без
   внешней сети (у сервера или у клиента) страница отдавалась, но ни одна кнопка
   учёбы не работала — все они на hx-post.
"""

import re
from pathlib import Path

import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient

from app.main import app
from tests.conftest import make_mock_bls

APP_DIR = Path(__file__).resolve().parents[1] / "app"
BASE_TEMPLATE = APP_DIR / "templates" / "base.html"
CARD_TEMPLATE = APP_DIR / "templates" / "partials" / "word_card.html"


@pytest.fixture
def client():
    return TestClient(app, raise_server_exceptions=True)


@pytest.fixture
def bls():
    return make_mock_bls()


def _login(client, bls):
    with patch("app.routers.auth.get_bls_client", return_value=bls):
        client.post("/login", data={"mode": "name", "name": "Test"}, follow_redirects=False)


def test_swapped_card_fragment_carries_no_script(client, bls):
    """Ответ на действие карточки не должен содержать <script> вовсе."""
    _login(client, bls)
    with patch("app.routers.study.get_bls_client", return_value=bls):
        resp = client.post("/study/lang1/show_answer")
    assert resp.status_code == 200
    assert "你好" in resp.text, "это должен быть фрагмент карточки"
    assert "<script" not in resp.text.lower(), (
        "скрипт внутри свопаемого фрагмента выполняется заново на каждый ответ")


def test_card_script_is_loaded_once_from_the_page_shell(client, bls):
    """Полная страница учёбы обязана подключать вынесенный файл ровно один раз."""
    _login(client, bls)
    with patch("app.routers.study.get_bls_client", return_value=bls):
        resp = client.get("/study/lang1")
    assert resp.status_code == 200
    assert resp.text.count("/static/js/word_card.js") == 1


def test_document_handlers_are_registered_outside_the_fragment():
    """
    Обработчики на document должны жить в файле, который грузится один раз.
    В шаблоне карточки их быть не может — он приезжает по hx-swap.
    """
    card = CARD_TEMPLATE.read_text(encoding="utf-8")
    assert "document.addEventListener" not in card
    script = (APP_DIR / "static" / "js" / "word_card.js").read_text(encoding="utf-8")
    assert script.count("document.addEventListener") == 4


def test_buttons_are_handled_by_delegation_not_per_element():
    """
    Раз скрипт больше не выполняется на каждый своп, навешивать обработчик на
    каждую кнопку нельзя: после подмены кнопки новые и остались бы немыми.
    """
    script = (APP_DIR / "static" / "js" / "word_card.js").read_text(encoding="utf-8")
    assert "closest('[hx-post]')" in script
    assert not re.search(r"querySelectorAll\(\s*'\[hx-post\]'\s*\)", script)


def test_htmx_is_served_locally_not_from_a_cdn(client):
    base = BASE_TEMPLATE.read_text(encoding="utf-8")
    assert "unpkg.com" not in base, "внешний CDN снова вернулся в base.html"
    assert "/static/vendor/htmx.min.js" in base

    resp = client.get("/static/vendor/htmx.min.js")
    assert resp.status_code == 200, "файл htmx должен реально лежать в static/vendor"
    assert "htmx" in resp.text[:2000]
