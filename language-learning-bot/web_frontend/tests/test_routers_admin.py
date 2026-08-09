"""Unit tests for web_frontend admin router. BLS client is mocked; sessions signed manually."""

import os
import json
import base64
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
from app.main import app

# Ключ берём из окружения, как само приложение: раньше он был
# зашит строкой, и тест ломался ровно тогда, когда продакшен
# переставал использовать заглушку — то есть при её починке.
SECRET_KEY = os.environ["SECRET_KEY"]


def _make_session_cookie(session_data: dict) -> str:
    """Create a signed session cookie matching Starlette's SessionMiddleware format."""
    import itsdangerous
    signer = itsdangerous.TimestampSigner(SECRET_KEY)
    data = base64.b64encode(json.dumps(session_data).encode()).decode()
    return signer.sign(data).decode()


ADMIN_SESSION = {"user_id": "admin-1", "first_name": "Admin", "is_admin": True}
USER_SESSION  = {"user_id": "user-1",  "first_name": "User",  "is_admin": False}


def _make_bls():
    bls = MagicMock()
    bls.admin_global_stats = AsyncMock(return_value={
        "total_users": 5,
        "languages": [{"id": "lang1", "name_ru": "Китайский", "name_foreign": "中文",
                       "word_count": 100, "active_users": 3}],
    })
    bls.admin_list_users = AsyncMock(return_value={
        "users": [{"id": "u1", "first_name": "Alice", "last_name": None,
                   "username": "alice", "telegram_id": 111, "is_admin": False}],
        "page": 1, "per_page": 20, "total": 1, "total_pages": 1,
    })
    bls.admin_user_details = AsyncMock(return_value={
        "user_id": "u1",
        "progress": [{"language_id": "lang1", "name_ru": "Китайский",
                      "words_studied": 5, "words_known": 3, "total_words": 100,
                      "progress_percentage": 5.0}],
    })
    bls.admin_toggle_admin = AsyncMock(return_value={"ok": True})
    bls.admin_create_language = AsyncMock(return_value={"ok": True, "result": {"id": "new1"}})
    bls.admin_update_language = AsyncMock(return_value={"ok": True})
    bls.admin_delete_language = AsyncMock(return_value={"ok": True})
    bls.admin_language_detail = AsyncMock(return_value={
        "id": "lang1", "name_ru": "Китайский", "name_foreign": "中文", "word_count": 100
    })
    bls.admin_list_words = AsyncMock(return_value={
        "words": [{"id": "w1", "number": 1, "foreign": "你好",
                   "translation": "привет", "transcription": "nǐhǎo"}],
        "page": 1, "total": 1, "total_pages": 1,
    })
    bls.admin_word_by_number = AsyncMock(return_value={
        "id": "w1", "number": 1, "foreign": "你好", "translation": "привет",
        "transcription": "nǐhǎo", "radicals": "", "references": "",
        "tones": "", "sounds": "",
    })
    bls.admin_update_word = AsyncMock(return_value={"ok": True})
    bls.admin_delete_word = AsyncMock(return_value={"ok": True})
    bls.admin_export_words = AsyncMock(return_value=b"BINARY")
    bls.admin_import_words = AsyncMock(return_value={"ok": True})
    bls.is_admin = AsyncMock(return_value=True)
    return bls


def _get(session: dict, url: str, bls=None, **kwargs):
    if bls is None:
        bls = _make_bls()
    cookie = _make_session_cookie(session)
    with patch("app.routers.admin.get_bls_client", return_value=bls):
        c = TestClient(app, raise_server_exceptions=True)
        return c.get(url, cookies={"session": cookie}, **kwargs), bls


def _post(session: dict, url: str, bls=None, **kwargs):
    if bls is None:
        bls = _make_bls()
    cookie = _make_session_cookie(session)
    with patch("app.routers.admin.get_bls_client", return_value=bls):
        c = TestClient(app, raise_server_exceptions=True)
        return c.post(url, cookies={"session": cookie}, **kwargs), bls


# ── Access control ────────────────────────────────────────────────────────────

def test_dashboard_requires_admin():
    r, _ = _get(USER_SESSION, "/admin", follow_redirects=False)
    assert r.status_code == 302
    assert r.headers["location"] == "/languages"


def test_dashboard_no_session_redirects_login():
    r, _ = _get({}, "/admin", follow_redirects=False)
    assert r.status_code == 302
    assert "/login" in r.headers["location"]


# ── Dashboard ─────────────────────────────────────────────────────────────────

def test_dashboard_ok():
    r, _ = _get(ADMIN_SESSION, "/admin")
    assert r.status_code == 200
    assert "Дашборд" in r.text
    assert "5" in r.text  # total_users


# ── Languages ─────────────────────────────────────────────────────────────────

def test_language_list():
    r, _ = _get(ADMIN_SESSION, "/admin/languages")
    assert r.status_code == 200
    assert "Китайский" in r.text


def test_create_language_redirects():
    bls = _make_bls()
    r, _ = _post(ADMIN_SESSION, "/admin/languages/create",
                 bls=bls,
                 data={"name_ru": "Японский", "name_foreign": "日本語"},
                 follow_redirects=False)
    assert r.status_code == 302
    bls.admin_create_language.assert_called_once()


def test_language_detail_page():
    r, _ = _get(ADMIN_SESSION, "/admin/languages/lang1")
    assert r.status_code == 200
    assert "Китайский" in r.text


def test_update_language():
    bls = _make_bls()
    r, _ = _post(ADMIN_SESSION, "/admin/languages/lang1/update",
                 bls=bls,
                 data={"name_ru": "Кит", "name_foreign": "中"},
                 follow_redirects=False)
    assert r.status_code == 302
    bls.admin_update_language.assert_called_once_with("admin-1", "lang1", "Кит", "中")


def test_delete_language():
    bls = _make_bls()
    r, _ = _post(ADMIN_SESSION, "/admin/languages/lang1/delete",
                 bls=bls, follow_redirects=False)
    assert r.status_code == 302
    bls.admin_delete_language.assert_called_once_with("admin-1", "lang1")


# ── Words ─────────────────────────────────────────────────────────────────────

def test_word_list_page():
    r, _ = _get(ADMIN_SESSION, "/admin/languages/lang1/words")
    assert r.status_code == 200
    assert "你好" in r.text


def test_word_search_by_number():
    r, _ = _get(ADMIN_SESSION, "/admin/languages/lang1/words?number=1")
    assert r.status_code == 200
    assert "привет" in r.text


def test_update_word():
    bls = _make_bls()
    r, _ = _post(ADMIN_SESSION, "/admin/words/w1/update",
                 bls=bls,
                 data={"language_id": "lang1", "field": "translation", "value": "привет2"},
                 follow_redirects=False)
    assert r.status_code == 302
    bls.admin_update_word.assert_called_once_with("admin-1", "w1", "translation", "привет2")


def test_delete_word():
    bls = _make_bls()
    r, _ = _post(ADMIN_SESSION, "/admin/words/w1/delete",
                 bls=bls, data={"language_id": "lang1"}, follow_redirects=False)
    assert r.status_code == 302
    bls.admin_delete_word.assert_called_once_with("admin-1", "w1")


# ── Export ────────────────────────────────────────────────────────────────────

def test_export_xlsx():
    r, _ = _get(ADMIN_SESSION, "/admin/languages/lang1/export?fmt=xlsx")
    assert r.status_code == 200
    assert r.content == b"BINARY"


# ── Users ─────────────────────────────────────────────────────────────────────

def test_user_list():
    r, _ = _get(ADMIN_SESSION, "/admin/users")
    assert r.status_code == 200
    assert "Alice" in r.text


def test_user_detail():
    r, _ = _get(ADMIN_SESSION, "/admin/users/u1")
    assert r.status_code == 200
    assert "u1" in r.text


def test_toggle_admin():
    bls = _make_bls()
    r, _ = _post(ADMIN_SESSION, "/admin/users/u1/toggle_admin",
                 bls=bls, data={"is_admin": "true"}, follow_redirects=False)
    assert r.status_code == 302
    bls.admin_toggle_admin.assert_called_once()


# ── Broadcast ─────────────────────────────────────────────────────────────────

def test_broadcast_page():
    r, _ = _get(ADMIN_SESSION, "/admin/broadcast")
    assert r.status_code == 200
    assert "Рассылка" in r.text
