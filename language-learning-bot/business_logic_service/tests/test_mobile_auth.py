"""Unit tests for mobile token auth (auth_service + /auth/mobile/* routes)."""

import time
import pytest
from app.services import auth_service


# ── auth_service unit tests ───────────────────────────────────────────────────

class TestMobileToken:
    def setup_method(self):
        auth_service._mobile_tokens.clear()

    def test_create_returns_6_char_code(self):
        code = auth_service.create_mobile_token("user1")
        assert len(code) == 6
        assert code.isalnum()
        assert code == code.upper()

    def test_activate_returns_user_id(self):
        code = auth_service.create_mobile_token("user42")
        user_id = auth_service.activate_mobile_token(code)
        assert user_id == "user42"

    def test_activate_is_single_use(self):
        code = auth_service.create_mobile_token("user1")
        auth_service.activate_mobile_token(code)
        assert auth_service.activate_mobile_token(code) is None

    def test_activate_unknown_code_returns_none(self):
        assert auth_service.activate_mobile_token("XXXXXX") is None

    def test_activate_case_insensitive(self):
        code = auth_service.create_mobile_token("user1")
        result = auth_service.activate_mobile_token(code.lower())
        assert result == "user1"

    def test_activate_expired_token(self):
        code = auth_service.create_mobile_token("user1")
        # Manually expire the token
        auth_service._mobile_tokens[code]["expires_at"] = time.time() - 1
        assert auth_service.activate_mobile_token(code) is None

    def test_cleanup_removes_old_mobile_tokens(self):
        code = auth_service.create_mobile_token("user1")
        auth_service._mobile_tokens[code]["expires_at"] = time.time() - 100
        auth_service._cleanup_expired()
        assert code not in auth_service._mobile_tokens

    def test_different_users_get_different_codes(self):
        codes = {auth_service.create_mobile_token(f"user{i}") for i in range(20)}
        assert len(codes) == 20  # all unique (probabilistically)


# ── FastAPI route integration tests ──────────────────────────────────────────

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


class TestMobileAuthRoutes:
    def setup_method(self):
        auth_service._mobile_tokens.clear()

    def test_create_returns_code_and_ttl(self):
        resp = client.post("/auth/mobile/create", json={"user_id": "u1"})
        assert resp.status_code == 200
        body = resp.json()
        assert "code" in body
        assert len(body["code"]) == 6
        assert body["ttl_seconds"] == 600

    def test_create_requires_user_id(self):
        resp = client.post("/auth/mobile/create", json={})
        assert resp.status_code == 400

    def test_activate_returns_user_id(self):
        code = client.post("/auth/mobile/create", json={"user_id": "u99"}).json()["code"]
        resp = client.post("/auth/mobile/activate", json={"code": code})
        assert resp.status_code == 200
        assert resp.json()["user_id"] == "u99"

    def test_activate_single_use(self):
        code = client.post("/auth/mobile/create", json={"user_id": "u1"}).json()["code"]
        client.post("/auth/mobile/activate", json={"code": code})
        resp = client.post("/auth/mobile/activate", json={"code": code})
        assert resp.status_code == 404

    def test_activate_invalid_code(self):
        resp = client.post("/auth/mobile/activate", json={"code": "ZZZZZZ"})
        assert resp.status_code == 404

    def test_activate_case_insensitive(self):
        code = client.post("/auth/mobile/create", json={"user_id": "u1"}).json()["code"]
        resp = client.post("/auth/mobile/activate", json={"code": code.lower()})
        assert resp.status_code == 200

    def test_activate_requires_code(self):
        resp = client.post("/auth/mobile/activate", json={})
        assert resp.status_code == 400
