"""
Учебный цикл: режим выбора, запрещённые пары и поведение при отказе BLS.

Эти ручки не дёргал ни один тест, а именно в них живёт самое неприятное:
pick_answer, add_forbidden_pair, clear_forbidden_pairs — и общий путь всех
карточных ответов, когда BLS вернул не-2xx. Клиент превращает такой ответ в {},
карточки в нём нет, а шаблон начинается с card.meta — пользователь получал 500
прямо внутри hx-swap, то есть экран замирал без единой кнопки: кнопки живут в
той же подменяемой области.
"""

import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient

from app.main import app
from tests.conftest import make_mock_bls, _make_card


@pytest.fixture
def client():
    return TestClient(app, raise_server_exceptions=True)


@pytest.fixture
def prod_client():
    """Как продакшен: необработанное исключение станет 500-ответом, а не упадёт в тест."""
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture
def bls():
    return make_mock_bls()


def _login(client, bls):
    with patch("app.routers.auth.get_bls_client", return_value=bls):
        resp = client.post("/login", data={"mode": "name", "name": "Test"},
                           follow_redirects=False)
    assert resp.status_code == 302


def _pick_card(**extra):
    card = _make_card()
    card["pick_options"] = {
        "target_modality": "text",
        "options": [
            {"word_id": "w-1", "target_text": "привет"},
            {"word_id": "w-2", "target_text": "спасибо"},
        ],
    }
    # Что BLS отдаёт в пик-режиме: свои кнопки, а не know/show_answer. Раньше
    # шаблон рисовал «Не знаю» сам и buttons[] в этом режиме не читал вовсе.
    if not extra.get("show_answer"):
        card["buttons"] = [
            {"id": "pick_dont_know", "text": "❓ Не знаю", "style": "outline-secondary"},
            {"id": "toggle_skip", "text": "⏩ Пропускать", "style": "outline-secondary"},
        ]
    card.update(extra)
    return card


# ── Отказ BLS на действии карточки ───────────────────────────────────────────

@pytest.mark.parametrize("method,url,data", [
    ("know_word",   "/study/lang1/know",        None),
    ("rate_word",   "/study/lang1/rate",        {"rating": "know"}),
    ("show_answer", "/study/lang1/show_answer", None),
    ("pick_answer", "/study/lang1/pick_answer", {"selected_word_id": "w-1"}),
    ("reconsider",  "/study/lang1/reconsider",  None),
    ("toggle_skip", "/study/lang1/toggle_skip", None),
])
def test_empty_bls_answer_gives_a_way_out_not_500(prod_client, bls, method, url, data):
    _login(prod_client, bls)
    setattr(bls, method, AsyncMock(return_value={}))

    with patch("app.routers.study.get_bls_client", return_value=bls):
        resp = prod_client.post(url, data=data or {})

    assert resp.status_code == 200, resp.text[:200]
    assert "Начать заново" in resp.text, "пользователю нужен выход, а не пустой экран"
    assert "/study/lang1" in resp.text


def test_lost_session_still_reports_itself_separately(prod_client, bls):
    """Потерянная сессия и пустой ответ BLS — разные причины, сообщения разные."""
    _login(prod_client, bls)
    bls.get_session = AsyncMock(return_value=None)

    with patch("app.routers.study.get_bls_client", return_value=bls):
        resp = prod_client.post("/study/lang1/know")

    assert resp.status_code == 200
    assert "Сессия не найдена" in resp.text
    assert "Начать заново" in resp.text


# ── Режим выбора ─────────────────────────────────────────────────────────────

def test_pick_mode_renders_every_option_as_a_button(client, bls):
    _login(client, bls)
    bls.get_session = AsyncMock(return_value={"session_id": "s1", "card": _pick_card()})

    with patch("app.routers.study.get_bls_client", return_value=bls):
        resp = client.get("/study/lang1")

    assert resp.status_code == 200
    assert "привет" in resp.text and "спасибо" in resp.text
    assert resp.text.count('hx-post="/study/lang1/pick_answer"') == 3, \
        "два варианта плюс «Не знаю»"
    assert '"selected_word_id": "w-1"' in resp.text
    assert "Не знаю" in resp.text


def test_pick_answer_forwards_the_chosen_word(client, bls):
    _login(client, bls)
    bls.pick_answer = AsyncMock(return_value={
        "session_id": "s1",
        "card": _pick_card(show_answer=True, pick_answer_result="wrong",
                           last_wrong_distractor_id="w-2"),
    })

    with patch("app.routers.study.get_bls_client", return_value=bls):
        resp = client.post("/study/lang1/pick_answer", data={"selected_word_id": "w-2"})

    assert resp.status_code == 200
    bls.pick_answer.assert_awaited_once_with("sess-1", "w-2")
    assert "Неверно" in resp.text
    # После неверного ответа предлагаем запретить именно этот дистрактор.
    assert '"bad_word_id": "w-2"' in resp.text


def test_pick_answer_on_exhausted_batch_shows_completion(client, bls):
    _login(client, bls)
    bls.pick_answer = AsyncMock(return_value={"session_id": "s1", "batch_exhausted": True})
    bls.next_batch = AsyncMock(return_value={"loaded": False})

    with patch("app.routers.study.get_bls_client", return_value=bls):
        resp = client.post("/study/lang1/pick_answer", data={"selected_word_id": "w-1"})

    assert resp.status_code == 200
    assert bls.get_progress.await_count == 1
    assert "你好" not in resp.text, "новой карточки быть не должно — батч кончился"


# ── Запрещённые пары ─────────────────────────────────────────────────────────

def _card_with_forbidden(count: int):
    card = _make_card(show_answer=True)
    card["extra_content"] = [
        {"type": "forbidden_quiz_pairs", "group": "forbidden",
         "word_ids": [f"bad-{i}" for i in range(count)]},
    ]
    return card


def test_forbidden_pairs_are_shown_with_a_way_to_clear_them(client, bls):
    _login(client, bls)
    bls.get_session = AsyncMock(return_value={"session_id": "s1",
                                              "card": _card_with_forbidden(3)})

    with patch("app.routers.study.get_bls_client", return_value=bls):
        resp = client.get("/study/lang1")

    assert resp.status_code == 200
    assert "Запрещённые варианты" in resp.text
    assert "Очистить запрещённые (3)" in resp.text
    assert 'hx-post="/study/lang1/clear_forbidden_pairs"' in resp.text


def test_forbidden_pairs_group_does_not_draw_an_empty_card(client, bls):
    """
    Элементы forbidden_quiz_pairs не рисуются в общем блоке extra — раньше из-за
    этого под словом оставался пустой белый прямоугольник.
    """
    _login(client, bls)
    bls.get_session = AsyncMock(return_value={"session_id": "s1",
                                              "card": _card_with_forbidden(1)})

    with patch("app.routers.study.get_bls_client", return_value=bls):
        resp = client.get("/study/lang1")

    assert resp.text.count('<div class="card shadow-sm mb-3">') == 0


def test_add_and_clear_forbidden_pairs_reach_bls(client, bls):
    _login(client, bls)
    bls.add_forbidden_pair = AsyncMock(return_value={"session_id": "s1",
                                                     "card": _card_with_forbidden(1)})
    bls.clear_forbidden_pairs = AsyncMock(return_value={"session_id": "s1",
                                                        "card": _make_card()})

    with patch("app.routers.study.get_bls_client", return_value=bls):
        added = client.post("/study/lang1/add_forbidden_pair", data={"bad_word_id": "bad-0"})
        cleared = client.post("/study/lang1/clear_forbidden_pairs")

    assert added.status_code == 200 and cleared.status_code == 200
    bls.add_forbidden_pair.assert_awaited_once_with("sess-1", "bad-0")
    bls.clear_forbidden_pairs.assert_awaited_once_with("sess-1")
    assert "Запрещённые варианты" not in cleared.text


@pytest.mark.parametrize("url,data", [
    ("/study/lang1/pick_answer", {"selected_word_id": "w-1"}),
    ("/study/lang1/add_forbidden_pair", {"bad_word_id": "bad-0"}),
    ("/study/lang1/clear_forbidden_pairs", {}),
    ("/study/lang1/toggle_skip", {}),
    ("/study/lang1/reconsider", {}),
])
def test_card_actions_require_login(client, url, data):
    """Обязательные поля формы нужны, чтобы дойти до проверки доступа, а не до 422."""
    resp = client.post(url, data=data, follow_redirects=False)
    assert resp.status_code == 302, url
    assert "/login" in resp.headers["location"], url
