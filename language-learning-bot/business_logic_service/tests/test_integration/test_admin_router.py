"""
Integration tests for BLS /admin router.
TestClient exercises real HTTP routing; api_client is injected via dependency_overrides;
is_admin() is patched at the module level (direct function call, not Depends).
"""

import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from app.main import app
from app.api.client import get_api_client


def _ok(result):
    return {"success": True, "result": result}


def _fail():
    return {"success": False, "result": None}


def _make_api():
    api = AsyncMock()
    api.get_users_count = AsyncMock(return_value=_ok({"count": 10}))
    api.get_languages = AsyncMock(return_value=_ok([
        {"id": "lang1", "name_ru": "Китайский", "name_foreign": "中文"},
    ]))
    api.get_word_count_by_language = AsyncMock(return_value=_ok({"count": 50}))
    api.get_language_active_users = AsyncMock(return_value=_ok({"count": 3}))
    api.get_users = AsyncMock(return_value=_ok([
        {"id": "u1", "first_name": "Alice", "telegram_id": 111, "is_admin": False},
    ]))
    api.update_user = AsyncMock(return_value=_ok({"is_admin": True}))
    api.get_language = AsyncMock(return_value=_ok(
        {"id": "lang1", "name_ru": "Китайский", "name_foreign": "中文"}))
    api.create_language = AsyncMock(return_value=_ok({"id": "new1"}))
    api.update_language = AsyncMock(return_value=_ok({}))
    api.delete_language = AsyncMock(return_value=_ok({}))
    api.get_words_by_language = AsyncMock(return_value=_ok([
        {"id": "w1", "number": 1, "foreign": "你好", "translation": "привет"},
    ]))
    api.get_word_by_number = AsyncMock(return_value=_ok(
        {"id": "w1", "number": 1, "foreign": "你好"}))
    api.update_word = AsyncMock(return_value=_ok({}))
    api.delete_word = AsyncMock(return_value=_ok({}))
    api.get_user_progress = AsyncMock(return_value=_ok(
        {"words_studied": 5, "words_known": 3}))
    api.export_words_by_language = AsyncMock(return_value=_ok(b"BINARY"))
    api.upload_words_file = AsyncMock(return_value=_ok({"imported": 10}))
    return api


def _client_with(api, is_admin_val=True):
    """Return (TestClient, api) with api injected and is_admin mocked."""
    app.dependency_overrides[get_api_client] = lambda: api
    patcher = patch("app.routers.admin.is_admin", AsyncMock(return_value=is_admin_val))
    patcher.start()
    client = TestClient(app, raise_server_exceptions=True)
    return client, patcher


def _cleanup(patcher):
    app.dependency_overrides.pop(get_api_client, None)
    patcher.stop()


# ── GET /admin/stats ──────────────────────────────────────────────────────────

def test_admin_stats_ok():
    api = _make_api()
    client, patcher = _client_with(api)
    try:
        r = client.get("/admin/stats", params={"user_id": "admin-1"})
        assert r.status_code == 200
        data = r.json()
        assert data["total_users"] == 10
        assert len(data["languages"]) == 1
    finally:
        _cleanup(patcher)


def test_admin_stats_forbidden():
    api = _make_api()
    client, patcher = _client_with(api, is_admin_val=False)
    try:
        r = client.get("/admin/stats", params={"user_id": "user-1"})
        assert r.status_code == 403
    finally:
        _cleanup(patcher)


# ── GET /admin/users ──────────────────────────────────────────────────────────

def test_admin_users_list():
    api = _make_api()
    client, patcher = _client_with(api)
    try:
        r = client.get("/admin/users", params={"user_id": "admin-1"})
        assert r.status_code == 200
        data = r.json()
        assert "users" in data
        assert data["page"] == 1
    finally:
        _cleanup(patcher)


def test_admin_users_page2_skip():
    api = _make_api()
    client, patcher = _client_with(api)
    try:
        client.get("/admin/users", params={"user_id": "admin-1", "page": 2})
        api.get_users.assert_called_with(skip=20, limit=20)
    finally:
        _cleanup(patcher)


# ── POST /admin/users/{id}/toggle_admin ──────────────────────────────────────

def test_toggle_admin_negates_value():
    api = _make_api()
    client, patcher = _client_with(api)
    try:
        r = client.post("/admin/users/u1/toggle_admin",
                        params={"user_id": "admin-1"},
                        json={"is_admin": False})
        assert r.status_code == 200
        assert r.json()["ok"] is True
        api.update_user.assert_called_once_with("u1", {"is_admin": True})
    finally:
        _cleanup(patcher)


# ── Language CRUD ─────────────────────────────────────────────────────────────

def test_create_language():
    api = _make_api()
    client, patcher = _client_with(api)
    try:
        r = client.post("/admin/languages",
                        params={"user_id": "admin-1"},
                        json={"name_ru": "Японский", "name_foreign": "日本語"})
        assert r.status_code == 200
        assert r.json()["ok"] is True
    finally:
        _cleanup(patcher)


def test_update_language():
    api = _make_api()
    client, patcher = _client_with(api)
    try:
        r = client.put("/admin/languages/lang1",
                       params={"user_id": "admin-1"},
                       json={"name_ru": "Кит", "name_foreign": "中"})
        assert r.status_code == 200
    finally:
        _cleanup(patcher)


def test_delete_language():
    api = _make_api()
    client, patcher = _client_with(api)
    try:
        r = client.delete("/admin/languages/lang1", params={"user_id": "admin-1"})
        assert r.status_code == 200
        assert r.json()["ok"] is True
    finally:
        _cleanup(patcher)


# ── Words ─────────────────────────────────────────────────────────────────────

def test_list_words():
    api = _make_api()
    client, patcher = _client_with(api)
    try:
        r = client.get("/admin/languages/lang1/words", params={"user_id": "admin-1"})
        assert r.status_code == 200
        assert len(r.json()["words"]) == 1
    finally:
        _cleanup(patcher)


def test_word_by_number():
    api = _make_api()
    client, patcher = _client_with(api)
    try:
        r = client.get("/admin/languages/lang1/words/by_number/1",
                       params={"user_id": "admin-1"})
        assert r.status_code == 200
        assert r.json()["number"] == 1
    finally:
        _cleanup(patcher)


def test_update_word_valid_field():
    api = _make_api()
    client, patcher = _client_with(api)
    try:
        r = client.patch("/admin/words/w1",
                         params={"user_id": "admin-1"},
                         json={"field": "translation", "value": "новый"})
        assert r.status_code == 200
        assert r.json()["ok"] is True
    finally:
        _cleanup(patcher)


def test_update_word_invalid_field():
    api = _make_api()
    client, patcher = _client_with(api)
    try:
        r = client.patch("/admin/words/w1",
                         params={"user_id": "admin-1"},
                         json={"field": "id", "value": "hack"})
        assert r.status_code == 400
    finally:
        _cleanup(patcher)


def test_delete_word():
    api = _make_api()
    client, patcher = _client_with(api)
    try:
        r = client.delete("/admin/words/w1", params={"user_id": "admin-1"})
        assert r.status_code == 200
    finally:
        _cleanup(patcher)


# ── Export / Import ───────────────────────────────────────────────────────────

def test_export_xlsx():
    api = _make_api()
    client, patcher = _client_with(api)
    try:
        r = client.get("/admin/languages/lang1/export",
                       params={"user_id": "admin-1", "format": "xlsx"})
        assert r.status_code == 200
        assert r.headers["content-type"].startswith(
            "application/vnd.openxmlformats-officedocument")
    finally:
        _cleanup(patcher)


def test_export_invalid_format():
    api = _make_api()
    client, patcher = _client_with(api)
    try:
        r = client.get("/admin/languages/lang1/export",
                       params={"user_id": "admin-1", "format": "pdf"})
        assert r.status_code == 400
    finally:
        _cleanup(patcher)


def test_import_words():
    api = _make_api()
    client, patcher = _client_with(api)
    try:
        r = client.post("/admin/languages/lang1/import",
                        params={"user_id": "admin-1"},
                        files={"file": ("words.xlsx", b"FILEDATA",
                                        "application/octet-stream")})
        assert r.status_code == 200
    finally:
        _cleanup(patcher)


# ── User details ──────────────────────────────────────────────────────────────

def test_user_details():
    api = _make_api()
    client, patcher = _client_with(api)
    try:
        r = client.get("/admin/users/u1", params={"user_id": "admin-1"})
        assert r.status_code == 200
        data = r.json()
        assert "user_id" in data
        assert "progress" in data
    finally:
        _cleanup(patcher)
