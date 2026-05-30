"""Shared fixtures for telegram_bot tests."""

import pytest
from unittest.mock import AsyncMock, MagicMock


def make_card(
    show_answer: bool = False,
    show_mode: str = "foreign",
    score: int = -1,
    is_skipped: bool = False,
    score_changed: bool = False,
    word_number: int = 1,
    correct: int = 0,
    incorrect: int = 0,
    language_name_ru: str = "",
    words_studied: int = 0,
    total_words: int = 0,
    words_for_today: int = 0,
) -> dict:
    """Build a minimal card dict matching BLS card_builder output shape."""
    if not show_answer:
        content = [
            {"type": "label", "text": "📝 Слово на иностранном:"},
            {"type": "foreign", "text": "hello"},
        ]
        buttons = [
            {"id": "know", "text": "✅ Знаю", "style": "success"},
            {"id": "show_answer", "text": "❓ Не знаю", "style": "outline-primary"},
            {"id": "toggle_skip",
             "text": "⏩ Не пропускать" if is_skipped else "⏩ Пропускать",
             "style": "outline-secondary"},
        ]
    else:
        content = [
            {"type": "label", "text": "🔍 Перевод:"},
            {"type": "translation", "text": "привет"},
            {"type": "label", "text": "🔊 Транскрипция:"},
            {"type": "transcription", "text": "[hɛˈloʊ]"},
            {"type": "label", "text": "📝 Слово на иностранном:"},
            {"type": "foreign", "text": "hello"},
        ]
        buttons = [
            {"id": "rate", "text": "➡️ Дальше", "style": "success",
             "rating": "know" if score_changed else "dont_know"},
            {"id": "toggle_skip",
             "text": "⏩ Не пропускать" if is_skipped else "⏩ Пропускать",
             "style": "outline-secondary"},
        ]

    badge_variant = "success" if score == 1 else ("danger" if score == 0 else "secondary")
    done = correct + incorrect
    return {
        "show_answer": show_answer,
        "content": content,
        "extra_content": [],
        "sounds": [],
        "buttons": buttons,
        "big_word": None,
        "meta": {
            "word_number": word_number,
            "score": score,
            "interval": 0,
            "next_check_date": "",
            "is_skipped": is_skipped,
            "session_pos": done + 1,
            "session_total": done + 1,
            "correct_count": correct,
            "incorrect_count": incorrect,
            "result_history": [],
            "pending_result": None,
            "score_badge": {"text": "новое", "variant": badge_variant, "next_date": ""},
            "language_name_ru": language_name_ru,
            "language_name_foreign": "",
            "words_studied": words_studied,
            "total_words": total_words,
            "words_for_today": words_for_today,
        },
    }


def make_session_resp(session_id: str = "sess-1", language_id: str = "lang1", **card_kwargs) -> dict:
    return {"session_id": session_id, "card": make_card(**card_kwargs)}


@pytest.fixture
def card_before():
    return make_card(show_answer=False)


@pytest.fixture
def card_after():
    return make_card(show_answer=True)


@pytest.fixture
def mock_bls():
    bls = AsyncMock()
    bls.get_or_create_user.return_value = {"status": 200, "data": {"id": "user-1"}}
    bls.get_languages.return_value = [
        {"id": "lang1", "name_ru": "Английский", "name_foreign": "English"},
        {"id": "lang2", "name_ru": "Китайский", "name_foreign": "中文"},
    ]
    bls.get_session.return_value = make_session_resp()
    bls.know_word.return_value = make_session_resp(show_answer=True, score_changed=True)
    bls.show_answer.return_value = make_session_resp(show_answer=True)
    bls.rate_word.return_value = make_session_resp()
    bls.toggle_skip.return_value = make_session_resp(is_skipped=True)
    bls.next_batch.return_value = {"loaded": False}
    return bls
