"""Tests for hint endpoints in study router."""

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
    import itsdangerous
    signer = itsdangerous.TimestampSigner(SECRET_KEY)
    data = base64.b64encode(json.dumps(session_data).encode()).decode()
    return signer.sign(data).decode()


USER_SESSION = {"user_id": "user-1", "first_name": "Test"}
HINTS_DATA = {
    "meaning": "ассоциация с солнцем",
    "phoneticsound": "",
    "phoneticassociation": "",
    "writing": "",
}


HINT_SETTINGS_ALL_ON = {
    "show_hint_meaning": True,
    "show_hint_phoneticsound": True,
    "show_hint_phoneticassociation": True,
    "show_hint_writing": True,
}


def _make_bls(hints=None, hint_settings=None):
    bls = MagicMock()
    bls.get_word_hints = AsyncMock(return_value=hints if hints is not None else HINTS_DATA)
    bls.get_hint_settings = AsyncMock(
        return_value=hint_settings if hint_settings is not None else HINT_SETTINGS_ALL_ON
    )
    bls.set_word_hint = AsyncMock(return_value=True)
    bls.delete_word_hint = AsyncMock(return_value=True)
    return bls


def _get(url: str, bls=None, session=None):
    if bls is None:
        bls = _make_bls()
    cookie = _make_session_cookie(session or USER_SESSION)
    with patch("app.routers.study.get_bls_client", return_value=bls):
        c = TestClient(app, raise_server_exceptions=True)
        return c.get(url, cookies={"session": cookie}), bls


def _post(url: str, data=None, bls=None, session=None):
    if bls is None:
        bls = _make_bls()
    cookie = _make_session_cookie(session or USER_SESSION)
    with patch("app.routers.study.get_bls_client", return_value=bls):
        c = TestClient(app, raise_server_exceptions=True)
        return c.post(url, data=data or {}, cookies={"session": cookie}), bls


def _delete(url: str, bls=None, session=None):
    if bls is None:
        bls = _make_bls()
    cookie = _make_session_cookie(session or USER_SESSION)
    with patch("app.routers.study.get_bls_client", return_value=bls):
        c = TestClient(app, raise_server_exceptions=True)
        return c.delete(url, cookies={"session": cookie}), bls


# ── GET /study/{language_id}/hints/{word_id} ──────────────────────────────────

class TestGetHints:
    def test_returns_200_with_panel(self):
        r, _ = _get("/study/lang1/hints/word-123")
        assert r.status_code == 200
        assert "hints-panel" in r.text

    def test_shows_existing_hint_text(self):
        r, _ = _get("/study/lang1/hints/word-123")
        assert "ассоциация с солнцем" in r.text

    def test_shows_hint_types(self):
        r, _ = _get("/study/lang1/hints/word-123")
        assert "Ассоциация (рус)" in r.text
        assert "Написание" in r.text

    def test_calls_bls_get_word_hints(self):
        _, bls = _get("/study/lang1/hints/word-123")
        bls.get_word_hints.assert_called_once_with("user-1", "word-123")

    def test_redirects_when_not_logged_in(self):
        bls = _make_bls()
        with patch("app.routers.study.get_bls_client", return_value=bls):
            c = TestClient(app, raise_server_exceptions=True)
            r = c.get("/study/lang1/hints/word-123", follow_redirects=False)
        assert r.status_code == 302

    def test_shows_add_button_for_empty_hint(self):
        hints = {"meaning": "", "phoneticsound": "", "phoneticassociation": "", "writing": ""}
        r, _ = _get("/study/lang1/hints/word-123",
                    bls=_make_bls(hints=hints, hint_settings=HINT_SETTINGS_ALL_ON))
        assert "➕" in r.text

    def test_shows_edit_and_delete_for_existing_hint(self):
        r, _ = _get("/study/lang1/hints/word-123")
        assert "✏️" in r.text
        assert "🗑" in r.text


# ── POST /study/{language_id}/hints/{word_id}/{hint_type} ─────────────────────

class TestSaveHint:
    def test_returns_200_with_panel(self):
        r, _ = _post("/study/lang1/hints/word-123/meaning", data={"text": "новый текст"})
        assert r.status_code == 200
        assert "hints-panel" in r.text

    def test_calls_set_word_hint_with_correct_args(self):
        bls = _make_bls()
        _, bls = _post("/study/lang1/hints/word-123/meaning",
                       data={"text": "новый текст"}, bls=bls)
        bls.set_word_hint.assert_called_once_with(
            "user-1", "word-123", "meaning", "новый текст", language_id="lang1"
        )

    def test_skips_save_for_empty_text(self):
        bls = _make_bls()
        r, bls = _post("/study/lang1/hints/word-123/meaning",
                       data={"text": "  "}, bls=bls)
        assert r.status_code == 200
        bls.set_word_hint.assert_not_called()

    def test_strips_whitespace_from_text(self):
        bls = _make_bls()
        _, bls = _post("/study/lang1/hints/word-123/writing",
                       data={"text": "  текст  "}, bls=bls)
        bls.set_word_hint.assert_called_once_with(
            "user-1", "word-123", "writing", "текст", language_id="lang1"
        )

    def test_refreshes_hints_after_save(self):
        bls = _make_bls()
        _post("/study/lang1/hints/word-123/meaning", data={"text": "text"}, bls=bls)
        bls.get_word_hints.assert_called_once_with("user-1", "word-123")


# ── Settings filtering ────────────────────────────────────────────────────────

class TestHintSettingsFiltering:
    def test_disabled_hint_type_not_shown_in_panel(self):
        """Hint type disabled in settings → not rendered in panel."""
        settings = {
            "show_hint_meaning": True,
            "show_hint_phoneticsound": False,
            "show_hint_phoneticassociation": False,
            "show_hint_writing": False,
        }
        r, _ = _get("/study/lang1/hints/word-123",
                    bls=_make_bls(hint_settings=settings))
        assert "Ассоциация (рус)" in r.text        # meaning — enabled
        assert "Звучание по слогам" not in r.text  # phoneticsound — disabled

    def test_all_types_disabled_shows_empty_panel(self):
        """All hint types off → panel renders with no hint rows."""
        settings = {
            "show_hint_meaning": False,
            "show_hint_phoneticsound": False,
            "show_hint_phoneticassociation": False,
            "show_hint_writing": False,
        }
        r, _ = _get("/study/lang1/hints/word-123",
                    bls=_make_bls(hint_settings=settings))
        # Panel should still appear (user navigated here), but no hint type rows
        assert r.status_code == 200
        assert "hints-panel" in r.text
        assert "Ассоциация" not in r.text

    def test_only_enabled_types_have_edit_forms(self):
        """POST endpoint only processes types the template would show — others silently ignored."""
        settings = {"show_hint_meaning": True}
        bls = _make_bls(hint_settings=settings)
        r, bls = _post("/study/lang1/hints/word-123/meaning",
                       data={"text": "текст"}, bls=bls)
        assert r.status_code == 200
        # meaning enabled → shown
        assert "Ассоциация (рус)" in r.text


# ── DELETE /study/{language_id}/hints/{word_id}/{hint_type} ──────────────────

class TestDeleteHint:
    def test_returns_200_with_panel(self):
        r, _ = _delete("/study/lang1/hints/word-123/meaning")
        assert r.status_code == 200
        assert "hints-panel" in r.text

    def test_calls_delete_word_hint(self):
        bls = _make_bls()
        _, bls = _delete("/study/lang1/hints/word-123/meaning", bls=bls)
        bls.delete_word_hint.assert_called_once_with("user-1", "word-123", "meaning")

    def test_refreshes_hints_after_delete(self):
        bls = _make_bls()
        _delete("/study/lang1/hints/word-123/meaning", bls=bls)
        bls.get_word_hints.assert_called_once_with("user-1", "word-123")

    def test_redirects_when_not_logged_in(self):
        bls = _make_bls()
        with patch("app.routers.study.get_bls_client", return_value=bls):
            c = TestClient(app, raise_server_exceptions=True)
            r = c.delete("/study/lang1/hints/word-123/meaning", follow_redirects=False)
        assert r.status_code == 302
