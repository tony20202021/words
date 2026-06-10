"""
Integration tests: BLS FastAPI app with a fully mocked api_client.
Tests exercise the real HTTP layer (TestClient) + real service logic,
but the backend (MongoDB API) is mocked at the api_client level.
"""

import pytest
from unittest.mock import AsyncMock
from fastapi.testclient import TestClient
from app.main import app
from app.api.client import get_api_client


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
        "result": [{"id": user_id, "first_name": "Test", "telegram_id": 123, "username": "Test"}],
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
def api():
    return make_api_client()


@pytest.fixture(autouse=True)
def override_api_client(api):
    app.dependency_overrides[get_api_client] = lambda: api
    yield
    app.dependency_overrides.pop(get_api_client, None)


@pytest.fixture
def client():
    return TestClient(app)


# ── User endpoint ─────────────────────────────────────────────────────────────

class TestUserEndpoint:
    def test_get_or_create_user(self, client, api):
        resp = client.post("/user/get_or_create", json={
            "telegram_id": 123, "first_name": "Test"
        })
        assert resp.status_code == 200
        assert resp.json()["user_id"] == "user-1"

    def test_user_not_found_returns_404(self, client, api):
        api.get_user_by_telegram_id.return_value = {"success": True, "result": []}
        api.create_user.return_value = {"success": False, "result": None, "error": "not found"}
        resp = client.post("/user/get_or_create", json={
            "telegram_id": 999, "first_name": "Ghost"
        })
        assert resp.status_code == 404


# ── Session endpoints ─────────────────────────────────────────────────────────

class TestSessionEndpoints:
    def _start(self, client, user_id="user-1", language_id="lang1"):
        return client.post("/session/start", json={
            "user_id": user_id, "language_id": language_id
        })

    def test_start_session_returns_card(self, client, api):
        resp = self._start(client)
        assert resp.status_code == 200
        data = resp.json()
        assert "session_id" in data
        assert data["card"] is not None
        assert data["card"]["meta"]["word_number"] == 1

    def test_start_session_no_words_returns_400(self, client, api):
        api.get_study_words.return_value = {"success": True, "result": []}
        resp = self._start(client)
        assert resp.status_code == 400

    def test_know_word_sets_score_changed(self, client, api):
        resp = self._start(client)
        session_id = resp.json()["session_id"]
        know_resp = client.post(f"/session/{session_id}/know")
        assert know_resp.status_code == 200
        card = know_resp.json()["card"]
        assert card["show_answer"] is True
        button_ids = [b["id"] for b in card["buttons"]]
        assert "rate" in button_ids
        assert "reconsider" in button_ids

    def test_show_answer_marks_incorrect(self, client, api):
        api.create_user_word_data.return_value = {
            "success": True,
            "result": {"score": 0, "check_interval": 0, "next_check_date": "2026-06-01", "is_skipped": False},
        }
        resp = self._start(client)
        session_id = resp.json()["session_id"]
        sa_resp = client.post(f"/session/{session_id}/show_answer")
        assert sa_resp.status_code == 200
        card = sa_resp.json()["card"]
        assert card["show_answer"] is True
        assert card["meta"]["incorrect_count"] == 1

    def test_rate_word_advances_index(self, client, api):
        resp = self._start(client)
        session_id = resp.json()["session_id"]
        client.post(f"/session/{session_id}/know")
        rate_resp = client.post(f"/session/{session_id}/rate", json={"rating": "know"})
        assert rate_resp.status_code == 200
        card = rate_resp.json()["card"]
        assert card["meta"]["word_number"] == 2

    def test_batch_exhausted_when_all_rated(self, client, api):
        api.get_study_words.return_value = {"success": True, "result": [_make_word(1)]}
        resp = self._start(client)
        session_id = resp.json()["session_id"]
        client.post(f"/session/{session_id}/know")
        rate_resp = client.post(f"/session/{session_id}/rate", json={"rating": "know"})
        assert rate_resp.json().get("batch_exhausted") is True

    def test_reconsider_flips_score(self, client, api):
        resp = self._start(client)
        session_id = resp.json()["session_id"]
        client.post(f"/session/{session_id}/know")
        recon_resp = client.post(f"/session/{session_id}/reconsider")
        assert recon_resp.status_code == 200
        card = recon_resp.json()["card"]
        assert card["meta"]["correct_count"] == 0
        assert card["meta"]["incorrect_count"] == 1


# ── Auth endpoints ────────────────────────────────────────────────────────────

class TestAuthEndpoints:
    def test_lookup_telegram_found(self, client, api):
        resp = client.post("/auth/lookup", json={"mode": "telegram", "telegram_id": 123})
        assert resp.status_code == 200
        assert resp.json()["found"] is True

    def test_lookup_telegram_not_found(self, client, api):
        api.get_user_by_telegram_id.return_value = {"success": True, "result": []}
        resp = client.post("/auth/lookup", json={"mode": "telegram", "telegram_id": 999})
        assert resp.status_code == 200
        assert resp.json()["found"] is False

    def test_lookup_name_found(self, client, api):
        resp = client.post("/auth/lookup", json={"mode": "name", "name": "Test"})
        assert resp.status_code == 200
        assert resp.json()["found"] is True

    def test_lookup_name_not_found(self, client, api):
        api.get_users.return_value = {"success": True, "result": []}
        resp = client.post("/auth/lookup", json={"mode": "name", "name": "NoOne"})
        assert resp.status_code == 200
        assert resp.json()["found"] is False

    def test_confirm_deny_token_flow(self, client, api):
        lookup = client.post("/auth/lookup", json={"mode": "telegram", "telegram_id": 123})
        token = lookup.json()["token"]

        status = client.get(f"/auth/status/{token}")
        assert status.json()["status"] == "pending"

        confirm = client.post(f"/auth/confirm/{token}")
        assert confirm.json()["ok"] is True

        status2 = client.get(f"/auth/status/{token}")
        assert status2.json()["status"] == "confirmed"
        assert status2.json()["user_id"] == "user-1"

    def test_deny_token(self, client, api):
        lookup = client.post("/auth/lookup", json={"mode": "telegram", "telegram_id": 123})
        token = lookup.json()["token"]

        client.post(f"/auth/deny/{token}")
        status = client.get(f"/auth/status/{token}")
        assert status.json()["status"] == "denied"

    def test_status_not_found(self, client):
        resp = client.get("/auth/status/nonexistent-token")
        assert resp.json()["status"] == "not_found"


# ── Finish stats trigger ──────────────────────────────────────────────────────

class TestFinishStatsTrigger:
    """
    _bg_update_finish_on_unknown must fire on every 'don't know' event,
    regardless of path:
      - direct rate{dont_know} (no prior show_answer)
      - show_answer → rate{dont_know}  (both trigger; second is harmless duplicate)
      - reconsider (know → change mind)
    rate{know}, rate{skip} must NOT trigger finish stats.
    """

    def _start(self, client):
        resp = client.post("/session/start", json={"user_id": "u1", "language_id": "lang1"})
        assert resp.status_code == 200
        return resp.json()["session_id"]

    def test_rate_dont_know_without_show_answer_triggers_finish_stats(self, client, api):
        """Direct rate{dont_know} must trigger first_finish + last_finish."""
        sid = self._start(client)
        resp = client.post(f"/session/{sid}/rate", json={"rating": "dont_know"})
        assert resp.status_code == 200
        api.update_daily_first_finish_statistics.assert_called_once()
        api.update_daily_last_finish_statistics.assert_called_once()

    def test_rate_dont_know_sends_incorrect_count_as_words_unknown(self, client, api):
        """finish stats receive the session incorrect_count (=1 after first error)."""
        sid = self._start(client)
        client.post(f"/session/{sid}/rate", json={"rating": "dont_know"})
        call_args = api.update_daily_last_finish_statistics.call_args
        payload = call_args.args[3] if len(call_args.args) > 3 else call_args.kwargs.get("stats_update", {})
        assert payload.get("words_unknown") == 1

    def test_rate_know_does_not_trigger_finish_stats(self, client, api):
        """rate{know} must NOT trigger finish stats."""
        sid = self._start(client)
        client.post(f"/session/{sid}/know")
        client.post(f"/session/{sid}/rate", json={"rating": "know"})
        api.update_daily_first_finish_statistics.assert_not_called()
        api.update_daily_last_finish_statistics.assert_not_called()

    def test_rate_skip_does_not_trigger_finish_stats(self, client, api):
        """rate{skip} must NOT trigger finish stats."""
        sid = self._start(client)
        resp = client.post(f"/session/{sid}/rate", json={"rating": "skip"})
        assert resp.status_code == 200
        api.update_daily_first_finish_statistics.assert_not_called()
        api.update_daily_last_finish_statistics.assert_not_called()

    def test_reconsider_triggers_finish_stats(self, client, api):
        """reconsider (know → dont_know) must trigger first_finish + last_finish."""
        sid = self._start(client)
        client.post(f"/session/{sid}/know")
        resp = client.post(f"/session/{sid}/reconsider")
        assert resp.status_code == 200
        api.update_daily_first_finish_statistics.assert_called()
        api.update_daily_last_finish_statistics.assert_called()

    def test_reconsider_sends_incorrect_count_as_words_unknown(self, client, api):
        """reconsider: finish stats receive incorrect_count=1."""
        sid = self._start(client)
        client.post(f"/session/{sid}/know")
        client.post(f"/session/{sid}/reconsider")
        call_args = api.update_daily_last_finish_statistics.call_args
        payload = call_args.args[3] if len(call_args.args) > 3 else call_args.kwargs.get("stats_update", {})
        assert payload.get("words_unknown") == 1

    def test_show_answer_then_rate_dont_know_triggers_finish_stats_twice(self, client, api):
        """show_answer + rate{dont_know}: both fire (second is harmless duplicate with same count)."""
        api.create_user_word_data.return_value = {
            "success": True,
            "result": {"score": 0, "check_interval": 0, "next_check_date": "2026-06-01", "is_skipped": False},
        }
        sid = self._start(client)
        client.post(f"/session/{sid}/show_answer")
        client.post(f"/session/{sid}/rate", json={"rating": "dont_know"})
        assert api.update_daily_first_finish_statistics.call_count == 2
        assert api.update_daily_last_finish_statistics.call_count == 2
