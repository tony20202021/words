"""Shared fixtures for web_frontend tests."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from fastapi.testclient import TestClient
from starlette.testclient import TestClient as StarletteTestClient


def make_mock_bls(
    user_id: str = "user-1",
    session_id: str = "sess-1",
):
    bls = MagicMock()

    bls.auth_lookup = AsyncMock(return_value={"found": True, "user_id": user_id, "first_name": "Test"})
    bls.auth_create = AsyncMock(return_value={"ok": True, "user_id": user_id, "first_name": "Test"})
    bls.auth_status = AsyncMock(return_value={"status": "pending"})

    bls.get_languages = AsyncMock(return_value=[
        {"id": "lang1", "name_ru": "Китайский", "name_foreign": "中文"},
    ])
    bls.get_statistics = AsyncMock(return_value={
        "words_for_today": 10, "words_studied": 5, "total_words": 100,
    })
    bls.get_session = AsyncMock(return_value={
        "session_id": session_id,
        "card": _make_card(),
    })
    bls.start_session = AsyncMock(return_value={
        "session_id": session_id,
        "card": _make_card(),
    })
    bls.show_answer = AsyncMock(return_value={"session_id": session_id, "card": _make_card(show_answer=True)})
    bls.know_word = AsyncMock(return_value={"session_id": session_id, "card": _make_card(show_answer=True, score_changed=True)})
    bls.rate_word = AsyncMock(return_value={"session_id": session_id, "card": _make_card()})
    bls.next_batch = AsyncMock(return_value={"loaded": True, "session_id": session_id, "card": _make_card()})
    bls.toggle_skip = AsyncMock(return_value={"session_id": session_id, "card": _make_card()})
    bls.reconsider = AsyncMock(return_value={"session_id": session_id, "card": _make_card(show_answer=True)})
    bls.get_progress = AsyncMock(return_value={"total_words_processed": 5, "remaining_in_batch": 3})
    bls.end_session = AsyncMock(return_value=None)

    return bls


def _make_card(show_answer: bool = False, score_changed: bool = False):
    return {
        "show_answer": show_answer,
        "score_changed": score_changed,
        "content": [
            {"type": "label", "text": "📝 Слово:"},
            {"type": "foreign", "text": "你好"},
        ],
        "sounds": [],
        "buttons": [
            {"id": "know", "text": "✅ Знаю", "style": "success"},
            {"id": "show_answer", "text": "❓ Не знаю", "style": "outline-primary"},
        ] if not show_answer else [
            {"id": "rate", "text": "✅ К следующему слову", "style": "success", "rating": "know"} if score_changed
            else {"id": "rate", "text": "➡️ Дальше", "style": "success", "rating": "dont_know"},
        ],
        "meta": {
            "word_number": 1, "score": -1, "interval": 0, "next_check_date": "",
            "is_skipped": False, "session_pos": 1, "correct_count": 0, "incorrect_count": 0,
            "score_badge": {"text": "новое", "variant": "secondary", "next_date": ""},
        },
    }
