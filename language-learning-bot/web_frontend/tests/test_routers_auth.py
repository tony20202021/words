"""Unit tests for web_frontend auth router."""

import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from app.main import app
from tests.conftest import make_mock_bls


@pytest.fixture
def client():
    return TestClient(app, raise_server_exceptions=True)


@pytest.fixture
def mock_bls():
    return make_mock_bls()


class TestLoginPage:
    def test_get_login_returns_200(self, client):
        resp = client.get("/login")
        assert resp.status_code == 200
        assert "Вход" in resp.text

    def test_logged_in_user_redirected(self, client):
        with client.session_transaction() as sess:
            sess["user_id"] = "u1"
        resp = client.get("/login", follow_redirects=False)
        assert resp.status_code == 302
        assert resp.headers["location"] == "/languages"


class TestLoginPostTelegram:
    def test_found_user_shows_pending_page(self, client, mock_bls):
        mock_bls.auth_lookup.return_value = {
            "found": True, "token": "tok-1", "message_sent": True, "first_name": "Test"
        }
        with patch("app.routers.auth.get_bls_client", return_value=mock_bls):
            resp = client.post("/login", data={"mode": "telegram", "telegram_id": "123"})
        assert resp.status_code == 200
        assert "tok-1" in resp.text

    def test_not_found_shows_create_offer(self, client, mock_bls):
        mock_bls.auth_lookup.return_value = {"found": False, "mode": "telegram"}
        with patch("app.routers.auth.get_bls_client", return_value=mock_bls):
            resp = client.post("/login", data={"mode": "telegram", "telegram_id": "123"})
        assert resp.status_code == 200
        assert "Пользователь не найден" in resp.text
        assert "Создать" in resp.text

    def test_missing_telegram_id_shows_error(self, client, mock_bls):
        with patch("app.routers.auth.get_bls_client", return_value=mock_bls):
            resp = client.post("/login", data={"mode": "telegram"})
        assert resp.status_code == 200
        assert "Введите Telegram ID" in resp.text


class TestLoginPostName:
    def test_found_user_redirects_to_languages(self, client, mock_bls):
        mock_bls.auth_lookup.return_value = {"found": True, "user_id": "u1", "first_name": "Антон"}
        with patch("app.routers.auth.get_bls_client", return_value=mock_bls):
            resp = client.post("/login", data={"mode": "name", "name": "Антон"},
                               follow_redirects=False)
        assert resp.status_code == 302
        assert resp.headers["location"] == "/languages"

    def test_multiple_users_shows_error(self, client, mock_bls):
        mock_bls.auth_lookup.return_value = {
            "found": "multiple",
            "users": [{"id": "u1", "first_name": "Антон"}, {"id": "u2", "first_name": "Антон"}],
        }
        with patch("app.routers.auth.get_bls_client", return_value=mock_bls):
            resp = client.post("/login", data={"mode": "name", "name": "Антон"})
        assert resp.status_code == 200
        assert "уточните" in resp.text.lower()

    def test_not_found_shows_create_offer(self, client, mock_bls):
        mock_bls.auth_lookup.return_value = {"found": False}
        with patch("app.routers.auth.get_bls_client", return_value=mock_bls):
            resp = client.post("/login", data={"mode": "name", "name": "Антон"})
        assert resp.status_code == 200
        assert "Пользователь не найден" in resp.text


class TestAuthCreate:
    def test_name_create_redirects_to_languages(self, client, mock_bls):
        mock_bls.auth_create.return_value = {"ok": True, "user_id": "u1", "first_name": "Антон"}
        with patch("app.routers.auth.get_bls_client", return_value=mock_bls):
            resp = client.post("/auth/create", data={"mode": "name", "first_name": "Антон"},
                               follow_redirects=False)
        assert resp.status_code == 302

    def test_telegram_create_shows_pending(self, client, mock_bls):
        mock_bls.auth_create.return_value = {
            "ok": True, "user_id": "u1", "token": "tok-1", "message_sent": True
        }
        with patch("app.routers.auth.get_bls_client", return_value=mock_bls):
            resp = client.post("/auth/create", data={
                "mode": "telegram", "telegram_id": "123", "first_name": "Антон"
            })
        assert resp.status_code == 200
        assert "tok-1" in resp.text


class TestAuthPoll:
    def test_pending_returns_spinner(self, client, mock_bls):
        mock_bls.auth_status.return_value = {"status": "pending"}
        with patch("app.routers.auth.get_bls_client", return_value=mock_bls):
            resp = client.get("/auth/poll?token=tok-1")
        assert resp.status_code == 200
        assert "spinner" in resp.text

    def test_confirmed_returns_hx_redirect(self, client, mock_bls):
        mock_bls.auth_status.return_value = {
            "status": "confirmed", "user_id": "u1", "telegram_id": 123
        }
        with patch("app.routers.auth.get_bls_client", return_value=mock_bls):
            resp = client.get("/auth/poll?token=tok-1")
        assert resp.status_code == 200
        assert resp.headers.get("hx-redirect") == "/languages"

    def test_denied_returns_error_message(self, client, mock_bls):
        mock_bls.auth_status.return_value = {"status": "denied"}
        with patch("app.routers.auth.get_bls_client", return_value=mock_bls):
            resp = client.get("/auth/poll?token=tok-1")
        assert resp.status_code == 200
        assert "отклонена" in resp.text.lower()


class TestAutologin:
    def test_found_user_redirects(self, client, mock_bls):
        mock_bls.auth_lookup.return_value = {"found": True, "user_id": "u1", "first_name": "Test"}
        with patch("app.routers.auth.get_bls_client", return_value=mock_bls):
            resp = client.get("/autologin?telegram_id=123", follow_redirects=False)
        assert resp.status_code == 302

    def test_not_found_shows_login(self, client, mock_bls):
        mock_bls.auth_lookup.return_value = {"found": False}
        with patch("app.routers.auth.get_bls_client", return_value=mock_bls):
            resp = client.get("/autologin?telegram_id=999")
        assert resp.status_code == 200
        assert "не найден" in resp.text.lower()
