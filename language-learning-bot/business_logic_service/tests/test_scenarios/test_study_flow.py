"""
Scenario tests for BLS session state machine.
Test complete user interaction flows using a mock api_client.
No HTTP, no database — pure logic.
"""

import pytest
from unittest.mock import AsyncMock
from app.services import session_service
from app.services.session_service import (
    start_session, know_word, show_answer_word, rate_word,
    toggle_word_skip, load_next_batch, get_current_word, get_progress,
)


# ── Mock API client ───────────────────────────────────────────────────────────

def make_word(number: int, word_id: str = None) -> dict:
    return {
        "_id": word_id or f"word-{number}",
        "word_number": number,
        "word_foreign": f"word{number}",
        "translation": f"слово{number}",
        "transcription": f"[w{number}]",
        "language_id": "lang1",
        "sounds": None,
    }


def make_mock_api(words: list = None, settings: dict = None) -> AsyncMock:
    """Return a mock api_client that returns given words list."""
    words = words or [make_word(i) for i in range(1, 6)]
    api = AsyncMock()

    # settings
    api.get_user_language_settings.return_value = {
        "success": True, "result": settings or {}
    }

    # words
    api.get_study_words.return_value = {"success": True, "result": words}

    # user word data: return empty by default (new word)
    api.get_user_word_data.return_value = {"success": True, "result": None}

    # create/update return the scored data
    def make_uwd(score: int = 1):
        return {"score": score, "check_interval": 1 if score == 1 else 0,
                "next_check_date": "2026-05-21", "is_skipped": False}

    api.create_user_word_data.return_value = {"success": True, "result": make_uwd(1)}
    api.update_user_word_data.return_value = {"success": True, "result": make_uwd(1)}

    return api


# ── Helpers ───────────────────────────────────────────────────────────────────

async def new_session(words=None, settings=None):
    api = make_mock_api(words=words, settings=settings)
    session = await start_session("u1", "lang1", api)
    assert session is not None, "Session creation failed"
    return session, api


# ── Start session ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_start_session_initial_state():
    session, _ = await new_session()
    assert session["current_index"] == 0
    assert session["show_answer"] is False
    assert session["word_processed"] is False
    assert session["score_changed"] is False
    assert session["correct_count"] == 0
    assert session["incorrect_count"] == 0
    assert session["total_words_processed"] == 0


@pytest.mark.asyncio
async def test_start_session_has_words():
    words = [make_word(1), make_word(2), make_word(3)]
    session, _ = await new_session(words=words)
    assert len(session["words"]) == 3
    assert get_current_word(session)["word_number"] == 1


# ── Know flow ─────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_know_sets_show_answer_and_scores():
    session, api = await new_session()
    session = await know_word(session, api)

    assert session["show_answer"] is True
    assert session["score_changed"] is True
    assert session["word_processed"] is True
    assert session["correct_count"] == 1
    assert session["total_words_processed"] == 0  # not advanced yet
    assert session["current_index"] == 0


@pytest.mark.asyncio
async def test_know_then_rate_advances():
    session, api = await new_session()
    session = await know_word(session, api)
    session = await rate_word(session, "know", api)

    assert session["current_index"] == 1
    assert session["show_answer"] is False
    assert session["score_changed"] is False
    assert session["word_processed"] is False
    assert session["correct_count"] == 1  # not double-counted


@pytest.mark.asyncio
async def test_know_does_not_double_score_on_repeat_call():
    session, api = await new_session()
    session = await know_word(session, api)
    session = await know_word(session, api)  # second call ignored

    assert session["correct_count"] == 1


# ── Don't know flow ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_show_answer_sets_show_answer_and_scores_incorrect():
    session, api = await new_session()
    session = await show_answer_word(session, api)

    assert session["show_answer"] is True
    assert session["word_processed"] is True
    assert session["score_changed"] is False
    assert session["incorrect_count"] == 1
    assert session["total_words_processed"] == 0  # not advanced yet
    assert session["current_index"] == 0


@pytest.mark.asyncio
async def test_show_answer_then_rate_advances():
    session, api = await new_session()
    session = await show_answer_word(session, api)
    session = await rate_word(session, "dont_know", api)

    assert session["current_index"] == 1
    assert session["show_answer"] is False
    assert session["incorrect_count"] == 1  # not double-counted


@pytest.mark.asyncio
async def test_show_answer_does_not_double_score_on_repeat_call():
    session, api = await new_session()
    session = await show_answer_word(session, api)
    session = await show_answer_word(session, api)  # second call ignored

    assert session["incorrect_count"] == 1


# ── Mixed flow ────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_mixed_know_and_dont_know():
    words = [make_word(i) for i in range(1, 4)]
    session, api = await new_session(words=words)

    # word 1: know
    session = await know_word(session, api)
    session = await rate_word(session, "know", api)
    assert session["correct_count"] == 1
    assert session["incorrect_count"] == 0
    assert session["total_words_processed"] == 1

    # word 2: don't know
    session = await show_answer_word(session, api)
    session = await rate_word(session, "dont_know", api)
    assert session["correct_count"] == 1
    assert session["incorrect_count"] == 1
    assert session["total_words_processed"] == 2

    # word 3: know
    session = await know_word(session, api)
    session = await rate_word(session, "know", api)
    assert session["correct_count"] == 2
    assert session["incorrect_count"] == 1
    assert session["total_words_processed"] == 3


# ── Toggle skip ───────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_toggle_skip_sets_is_skipped():
    session, api = await new_session()
    word = get_current_word(session)
    assert not (word.get("user_word_data") or {}).get("is_skipped", False)

    api.create_user_word_data.return_value = {
        "success": True,
        "result": {"is_skipped": True, "score": -1, "check_interval": 0}
    }
    session = await toggle_word_skip(session, api)
    word = get_current_word(session)
    assert word["user_word_data"]["is_skipped"] is True


@pytest.mark.asyncio
async def test_toggle_skip_does_not_advance():
    session, api = await new_session()
    session = await toggle_word_skip(session, api)
    assert session["current_index"] == 0


# ── Batch exhaustion ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_batch_exhausted_after_all_words():
    words = [make_word(1), make_word(2)]
    session, api = await new_session(words=words)

    for _ in words:
        session = await know_word(session, api)
        session = await rate_word(session, "know", api)

    assert get_current_word(session) is None


@pytest.mark.asyncio
async def test_load_next_batch_when_exhausted():
    next_words = [make_word(3), make_word(4)]
    api = make_mock_api(words=[make_word(1)])
    session = await start_session("u1", "lang1", api)

    # exhaust first batch
    session = await know_word(session, api)
    session = await rate_word(session, "know", api)
    assert get_current_word(session) is None

    # return new words on next call
    api.get_study_words.return_value = {"success": True, "result": next_words}
    loaded = await load_next_batch(session, api)
    assert loaded is True
    assert get_current_word(session)["word_number"] == 3


@pytest.mark.asyncio
async def test_no_more_batches_returns_false():
    api = make_mock_api(words=[make_word(1)])
    session = await start_session("u1", "lang1", api)

    session = await know_word(session, api)
    session = await rate_word(session, "know", api)

    # no more words anywhere
    api.get_study_words.return_value = {"success": True, "result": []}
    loaded = await load_next_batch(session, api)
    assert loaded is False


# ── Progress ──────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_progress_tracking():
    words = [make_word(i) for i in range(1, 4)]
    session, api = await new_session(words=words)

    progress = get_progress(session)
    assert progress["total_words_processed"] == 0
    assert progress["remaining_in_batch"] == 3

    session = await know_word(session, api)
    session = await rate_word(session, "know", api)
    progress = get_progress(session)
    assert progress["total_words_processed"] == 1
    assert progress["remaining_in_batch"] == 2


# ── show_mode changes on advance ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_show_mode_resets_on_advance():
    session, api = await new_session()
    initial_mode = session["show_mode"]

    # advance through several words — mode is random but session tracks it
    session = await know_word(session, api)
    session = await rate_word(session, "know", api)

    assert "show_mode" in session
    assert session["show_answer"] is False


# ── words_for_today counter ───────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_session_pos_increments_correctly():
    words = [make_word(i) for i in range(1, 4)]
    session, api = await new_session(words=words)

    assert session["total_words_processed"] == 0

    session = await know_word(session, api)
    assert session["total_words_processed"] == 0  # scored but not advanced

    session = await rate_word(session, "know", api)
    assert session["total_words_processed"] == 1  # advanced → incremented

    session = await show_answer_word(session, api)
    assert session["total_words_processed"] == 1  # scored but not advanced

    session = await rate_word(session, "dont_know", api)
    assert session["total_words_processed"] == 2  # advanced → incremented


# ── result_history ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_result_history_appended_after_know():
    session, api = await new_session()
    session = await know_word(session, api)
    session = await rate_word(session, "know", api)
    assert "know" in session["result_history"]


@pytest.mark.asyncio
async def test_result_history_appended_after_dont_know():
    session, api = await new_session()
    session = await show_answer_word(session, api)
    session = await rate_word(session, "dont_know", api)
    assert "dont_know" in session["result_history"]


@pytest.mark.asyncio
async def test_result_history_appended_even_when_word_processed():
    """Regression: result_history must be appended outside the word_processed guard."""
    session, api = await new_session()
    session = await know_word(session, api)          # sets word_processed=True
    session = await rate_word(session, "know", api)  # word_processed already True
    assert len(session["result_history"]) == 1
    assert session["result_history"][0] == "know"


@pytest.mark.asyncio
async def test_result_history_accumulates_across_words():
    words = [make_word(i) for i in range(1, 4)]
    session, api = await new_session(words=words)

    session = await know_word(session, api)
    session = await rate_word(session, "know", api)
    session = await show_answer_word(session, api)
    session = await rate_word(session, "dont_know", api)
    session = await know_word(session, api)
    session = await rate_word(session, "know", api)

    assert session["result_history"] == ["know", "dont_know", "know"]


# ── reconsider ────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_reconsider_flips_score_changed():
    from app.services.session_service import reconsider_word
    session, api = await new_session()
    session = await know_word(session, api)
    assert session["score_changed"] is True

    session = await reconsider_word(session, api)
    assert session["score_changed"] is False


@pytest.mark.asyncio
async def test_reconsider_does_not_advance():
    from app.services.session_service import reconsider_word
    session, api = await new_session()
    session = await know_word(session, api)
    idx_before = session["current_index"]

    session = await reconsider_word(session, api)
    assert session["current_index"] == idx_before
