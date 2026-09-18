"""
Авторизация BLS: кто вызывает и вправе ли он действовать за этого пользователя.

До неё BLS верил присланному user_id на слово, а все ручки были открыты в
интернет. Здесь закреплено, что в режиме enforce:
  - аноним получает 401, чужой пользователь — 403;
  - служба (веб, бот) действует за любого по ключу;
  - нельзя выпустить одноразовый код входа за ЧУЖОЙ user_id — иначе код
    активируется на своём телефоне, и вся защита обходится одним запросом.

Прежние тесты идут в режиме log (conftest), здесь режим переключается явно.
"""

import pytest
from unittest.mock import AsyncMock, patch
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient

from app.main import app
from app.api.client import get_api_client
from app import auth_guard
from app.services import auth_service
from common import auth_keys

SERVICE = {"X-Service-Key": "test-service-key-not-for-production"}


def bearer(user_id):
    return {"Authorization": f"Bearer {auth_guard.issue_token(user_id)}"}


def _make_api():
    api = AsyncMock()
    ok_word = {"success": True, "result": {"score": 1, "check_interval": 1,
               "next_check_date": "2026-06-01", "is_skipped": False}}
    api.get_user_language_settings.return_value = {"success": True, "result": {}}
    api.update_user_language_settings.return_value = {"success": True, "result": {}}
    api.get_study_words.return_value = {"success": True, "result": [
        {"_id": "w1", "word_number": 1, "word_foreign": "x", "translation": "y",
         "transcription": "", "language_id": "lang1", "sounds": None}]}
    api.get_user_word_data.return_value = {"success": True, "result": None}
    api.create_user_word_data.return_value = ok_word
    api.update_user_word_data.return_value = ok_word
    api.get_user_progress.return_value = {"success": True, "result": {}}
    api.get_daily_first_finish_statistics.return_value = {
        "success": True, "status": 404, "result": None}
    api.get_languages.return_value = {"success": True, "result": []}
    return api


@pytest.fixture
def api():
    return _make_api()


@pytest.fixture(autouse=True)
def _override_api(api):
    app.dependency_overrides[get_api_client] = lambda: api
    yield
    app.dependency_overrides.pop(get_api_client, None)


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def enforce(monkeypatch):
    monkeypatch.setattr(auth_keys, "auth_mode", lambda: "enforce")


def _allowed(resp):
    """Авторизацию прошёл. Что ответит сам обработчик на заглушке — не предмет теста."""
    return resp.status_code not in (401, 403)


# ── токены ───────────────────────────────────────────────────────────────────

def test_token_names_its_owner():
    assert auth_guard.verify_token(auth_guard.issue_token("u1")) == "u1"


def test_tampered_token_is_rejected():
    token = auth_guard.issue_token("u1")
    assert auth_guard.verify_token(token[:-2] + "xx") is None


def test_token_cannot_be_moved_to_another_user():
    """Подпись привязана к user_id: заменить его в токене нельзя."""
    sig = auth_guard.issue_token("u1").rpartition(".")[2]
    assert auth_guard.verify_token(f"u2.{sig}") is None


def test_activation_by_code_hands_out_a_token(client):
    code = auth_service.create_mobile_token("u1")
    resp = client.post("/auth/mobile/activate", json={"code": code})
    assert resp.status_code == 200
    assert auth_guard.verify_token(resp.json()["token"]) == "u1"


# ── каждая ручка классифицирована ────────────────────────────────────────────

def test_every_route_is_classified():
    """
    Новая ручка без пользователя в пути молча стала бы открытой. Здесь каждая
    обязана попасть в один из разрядов — иначе тест назовёт её.
    """
    loose = []
    for route in app.routes:
        if not isinstance(route, APIRoute):
            continue
        p = route.path
        classified = (
            p in auth_guard.PUBLIC_ROUTES
            or p in auth_guard.SERVICE_ROUTES
            or p in auth_guard.BODY_USER_ROUTES
            or "{user_id}" in p or "{session_id}" in p
            or p.startswith("/admin")
        )
        if not classified:
            loose.append(f"{sorted(route.methods)} {p}")
    assert not loose, "ручки без разряда авторизации:\n" + "\n".join(loose)


# ── принуждение ──────────────────────────────────────────────────────────────

def test_anonymous_gets_401(client, enforce):
    assert client.get("/settings/u1/lang1").status_code == 401


def test_own_token_passes(client, enforce):
    assert client.get("/settings/u1/lang1", headers=bearer("u1")).status_code == 200


def test_someone_elses_data_is_403(client, enforce):
    assert client.get("/settings/u1/lang1", headers=bearer("u2")).status_code == 403


def test_service_acts_for_anyone(client, enforce):
    assert client.get("/settings/u1/lang1", headers=SERVICE).status_code == 200


def test_public_routes_need_nothing(client, enforce):
    assert client.get("/version").status_code == 200


def test_user_cannot_call_service_routes(client, enforce):
    resp = client.post("/user/get_or_create", json={"telegram_id": 1, "first_name": "x"},
                       headers=bearer("u1"))
    assert resp.status_code == 403


def test_service_calls_service_routes(client, enforce):
    resp = client.post("/user/get_or_create", json={"telegram_id": 1, "first_name": "x"},
                       headers=SERVICE)
    assert _allowed(resp)


def test_offline_batch_only_for_oneself(client, enforce):
    body = {"user_id": "u1", "language_id": "lang1", "events": []}
    assert client.post("/results/batch", json=body, headers=bearer("u2")).status_code == 403
    assert _allowed(client.post("/results/batch", json=body, headers=bearer("u1")))


def test_login_code_cannot_be_issued_for_someone_else(client, enforce):
    """
    Та самая дыра. Выпустив код за чужой user_id и активировав его на своём
    телефоне, можно было получить чужой токен — и вся защита обходилась бы
    одним запросом. Выпускать код можно только для себя.
    """
    assert client.post("/auth/mobile/create", json={"user_id": "victim"},
                       headers=bearer("attacker")).status_code == 403
    assert client.post("/auth/mobile/create", json={"user_id": "victim"}).status_code == 401
    assert _allowed(client.post("/auth/mobile/create", json={"user_id": "u1"},
                                headers=bearer("u1")))


def test_session_belongs_to_its_owner(client, enforce):
    """В ручках сессии пользователя в пути нет — хозяин берётся из самой сессии."""
    sid = client.post("/session/start", json={"user_id": "u1", "language_id": "lang1"},
                      headers=SERVICE).json()["session_id"]
    assert _allowed(client.post(f"/session/{sid}/show_answer", headers=bearer("u1")))
    assert client.post(f"/session/{sid}/show_answer", headers=bearer("u2")).status_code == 403


def test_admin_trusts_the_token_not_the_query(client, enforce):
    """Прежде админкой становился любой, кто подставит в запрос id админа."""
    resp = client.get("/admin/stats", params={"user_id": "admin-1"}, headers=bearer("u2"))
    assert resp.status_code == 403


# ── режим журнала ────────────────────────────────────────────────────────────

def test_log_mode_lets_violations_through_but_records_them(client):
    """С него начинается выкладка: видно, кто ещё без токена, никто не отрезан."""
    with patch.object(auth_guard.logger, "warning") as warn:
        resp = client.get("/settings/u1/lang1")
    assert resp.status_code == 200
    assert warn.called
    assert "нет удостоверения" in warn.call_args.args[0]
