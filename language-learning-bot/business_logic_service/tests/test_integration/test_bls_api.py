"""
Integration tests: BLS FastAPI app with a fully mocked api_client.
Tests exercise the real HTTP layer (TestClient) + real service logic,
but the backend (MongoDB API) is mocked at the api_client level.
"""

import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from app.main import app


# ── Mock api_client factory ───────────────────────────────────────────────────

def make_api_client(words=None, user_id="user-1"):
    api = AsyncMock()

    api.get_user_by_telegram_id.return_value = {
        "success": True,
        "result": [{"id": user_id, "first_name": "Test", "telegram_id": 123}],
    }
    api.create_user.return_value = {
        "success": True,
        "result": {"id": user_id, "first_name": "Test"},
    }
    api.get_users.return_value = {
        "success": True,
        "result": [{"id": user_id, "first_name": "Test", "telegram_id": 123}],
    }
    api.get_user_language_settings.return_value = {"success": True, "result": {}}
    api.get_study_words.return_value = {
        "success": True,
        "result": words or [_make_word(i) for i in range(1, 4)],
    }
    api.get_user_word_data.return_value = {"success": True, "result": None}
    api.create_user_word_data.return_value = {
        "success": True,
        "result": {"score": 1, "check_interval": 1, "next_check_date": "2026-06-01", "is_skipped": False},
    }
    api.update_user_word_data.return_value = {
        "success": True,
        "result": {"score": 1, "check_interval": 1, "next_check_date": "2026-06-01", "is_skipped": False},
    }
    api.get_languages.return_value = {
        "success": True,
        "result": [{"id": "lang1", "name_ru": "Китайский", "name_foreign": "中文"}],
    }
    api.get_user_progress.return_value = {"success": True, "result": {}}
    return api


def _make_word(n: int) -> dict:
    return {
        "_id": f"word-{n}", "word_number": n,
        "word_foreign": f"word{n}", "translation": f"слово{n}",
        "transcription": f"[w{n}]", "language_id": "lang1", "sounds": None,
    }


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def api():
    return make_api_client()


# ── User endpoint ─────────────────────────────────────────────────────────────

class TestUserEndpoint:
    def test_get_or_create_user(self, client, api):
        with patch("app.routers.user.get_api_client", return_value=api):
            resp = client.post("/user/get_or_create", json={
                "telegram_id": 123, "first_name": "Test"
            })
        assert resp.status_code == 200
        assert resp.json()["user_id"] == "user-1"

    def test_user_not_found_returns_404(self, client, api):
        api.get_user_by_telegram_id.return_value = {"success": True, "result": []}
        api.create_user.return_value = {"success": False, "result": None}
        with patch("app.routers.user.get_api_client", return_value=api):
            resp = client.post("/user/get_or_create", json={
                "telegram_id": 999, "first_name": "Ghost"
            })
        assert resp.status_code == 404


# ── Session endpoints ─────────────────────────────────────────────────────────

class TestSessionEndpoints:
    def _start(self, client, api, user_id="user-1", language_id="lang1"):
        with patch("app.routers.session.get_api_client", return_value=api):
            return client.post("/session/start", json={
                "user_id": user_id, "language_id": language_id
            })

    def test_start_session_returns_card(self, client, api):
        resp = self._start(client, api)
        assert resp.status_code == 200
        data = resp.json()
        assert "session_id" in data
        assert data["card"] is not None
        assert data["card"]["meta"]["word_number"] == 1

    def test_start_session_no_words_returns_400(self, client, api):
        api.get_study_words.return_value = {"success": True, "result": []}
        resp = self._start(client, api)
        assert resp.status_code == 400

    def test_know_word_sets_score_changed(self, client, api):
        resp = self._start(client, api)
        session_id = resp.json()["session_id"]
        with patch("app.routers.session.get_api_client", return_value=api):
            know_resp = client.post(f"/session/{session_id}/know")
        assert know_resp.status_code == 200
        card = know_resp.json()["card"]
        assert card["show_answer"] is True
        # After know: К следующему слову button
        button_ids = [b["id"] for b in card["buttons"]]
        assert "rate" in button_ids
        assert "reconsider" in button_ids

    def test_show_answer_marks_incorrect(self, client, api):
        api.create_user_word_data.return_value = {
            "success": True,
            "result": {"score": 0, "check_interval": 0, "next_check_date": "2026-06-01", "is_skipped": False},
        }
        resp = self._start(client, api)
        session_id = resp.json()["session_id"]
        with patch("app.routers.session.get_api_client", return_value=api):
            sa_resp = client.post(f"/session/{session_id}/show_answer")
        assert sa_resp.status_code == 200
        card = sa_resp.json()["card"]
        assert card["show_answer"] is True
        assert card["meta"]["incorrect_count"] == 1

    def test_rate_word_advances_index(self, client, api):
        resp = self._start(client, api)
        session_id = resp.json()["session_id"]
        with patch("app.routers.session.get_api_client", return_value=api):
            client.post(f"/session/{session_id}/know")
            rate_resp = client.post(f"/session/{session_id}/rate", json={"rating": "know"})
        assert rate_resp.status_code == 200
        card = rate_resp.json()["card"]
        assert card["meta"]["word_number"] == 2

    def test_batch_exhausted_when_all_rated(self, client, api):
        api.get_study_words.return_value = {"success": True, "result": [_make_word(1)]}
        resp = self._start(client, api)
        session_id = resp.json()["session_id"]
        with patch("app.routers.session.get_api_client", return_value=api):
            client.post(f"/session/{session_id}/know")
            rate_resp = client.post(f"/session/{session_id}/rate", json={"rating": "know"})
        assert rate_resp.json().get("batch_exhausted") is True

    def test_reconsider_flips_score(self, client, api):
        resp = self._start(client, api)
        session_id = resp.json()["session_id"]
        with patch("app.routers.session.get_api_client", return_value=api):
            client.post(f"/session/{session_id}/know")
            recon_resp = client.post(f"/session/{session_id}/reconsider")
        assert recon_resp.status_code == 200
        card = recon_resp.json()["card"]
        # After reconsider: correct_count should be 0, incorrect_count should be 1
        assert card["meta"]["correct_count"] == 0
        assert card["meta"]["incorrect_count"] == 1


# ── Auth endpoints ────────────────────────────────────────────────────────────

class TestAuthEndpoints:
    def test_lookup_telegram_found(self, client, api):
        with patch("app.routers.auth.get_api_client", return_value=api):
            resp = client.post("/auth/lookup", json={"mode": "telegram", "telegram_id": 123})
        assert resp.status_code == 200
        assert resp.json()["found"] is True

    def test_lookup_telegram_not_found(self, client, api):
        api.get_user_by_telegram_id.return_value = {"success": True, "result": []}
        with patch("app.routers.auth.get_api_client", return_value=api):
            resp = client.post("/auth/lookup", json={"mode": "telegram", "telegram_id": 999})
        assert resp.status_code == 200
        assert resp.json()["found"] is False

    def test_lookup_name_found(self, client, api):
        with patch("app.routers.auth.get_api_client", return_value=api):
            resp = client.post("/auth/lookup", json={"mode": "name", "name": "Test"})
        assert resp.status_code == 200
        assert resp.json()["found"] is True

    def test_lookup_name_not_found(self, client, api):
        api.get_users.return_value = {"success": True, "result": []}
        with patch("app.routers.auth.get_api_client", return_value=api):
            resp = client.post("/auth/lookup", json={"mode": "name", "name": "NoOne"})
        assert resp.status_code == 200
        assert resp.json()["found"] is False

    def test_confirm_deny_token_flow(self, client, api):
        # Lookup creates a token
        with patch("app.routers.auth.get_api_client", return_value=api):
            lookup = client.post("/auth/lookup", json={"mode": "telegram", "telegram_id": 123})
        token = lookup.json()["token"]

        # Status: pending
        status = client.get(f"/auth/status/{token}")
        assert status.json()["status"] == "pending"

        # Confirm
        confirm = client.post(f"/auth/confirm/{token}")
        assert confirm.json()["ok"] is True

        # Status: confirmed
        status2 = client.get(f"/auth/status/{token}")
        assert status2.json()["status"] == "confirmed"
        assert status2.json()["user_id"] == "user-1"

    def test_deny_token(self, client, api):
        with patch("app.routers.auth.get_api_client", return_value=api):
            lookup = client.post("/auth/lookup", json={"mode": "telegram", "telegram_id": 123})
        token = lookup.json()["token"]

        client.post(f"/auth/deny/{token}")
        status = client.get(f"/auth/status/{token}")
        assert status.json()["status"] == "denied"

    def test_status_not_found(self, client):
        resp = client.get("/auth/status/nonexistent-token")
        assert resp.json()["status"] == "not_found"
