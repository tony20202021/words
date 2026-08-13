"""
Tests for the offline caching support in BLS:
- build_bundle: pre-renders both card sides and must NOT clobber the user's
  active online session (register=False snapshot).
- apply_results_batch: validates events, applies valid ones, idempotent by event_id.

Pure logic — mock api_client, no HTTP, no DB.
"""

import pytest
from unittest.mock import AsyncMock

from app.services import session_service
from app.services.session_service import (
    build_bundle, apply_results_batch, start_session, get_session,
)


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
    words = words or [make_word(i) for i in range(1, 4)]
    api = AsyncMock()
    api.get_user_language_settings.return_value = {"success": True, "result": settings or {}}
    api.get_study_words.return_value = {"success": True, "result": words}
    api.get_user_word_data.return_value = {"success": True, "result": None}
    uwd = {"score": 1, "check_interval": 1, "next_check_date": "2026-05-21", "is_skipped": False}
    api.create_user_word_data.return_value = {"success": True, "result": uwd}
    api.update_user_word_data.return_value = {"success": True, "result": uwd}
    api.get_user_progress.return_value = {
        "result": {"language_name_ru": "Иврит", "language_name_foreign": "עברית",
                   "words_studied": 5, "total_words": 10, "words_for_today": 3}
    }
    return api


# ── build_bundle ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_build_bundle_pre_renders_both_card_sides():
    api = make_mock_api(words=[make_word(i) for i in range(1, 4)], settings={"random_pick_mode": False})
    bundle = await build_bundle("u1", "lang1", api)
    assert bundle is not None
    assert len(bundle["words"]) == 3
    for unit in bundle["words"]:
        assert unit["word_id"]
        assert unit["card_front"]["show_answer"] is False
        assert unit["card_answer"]["show_answer"] is True
        assert "sounds" in unit
    assert bundle["total_words"] == 10
    assert bundle["words_for_today"] == 3


@pytest.mark.asyncio
async def test_build_bundle_advances_session_position_per_unit():
    """
    Regression: build_bundle rendered every card from the same non-advancing
    snapshot, so meta.session_pos was 1 on all of them and the Android offline
    screen showed "1 из N" for the whole session.
    """
    api = make_mock_api(words=[make_word(i) for i in range(1, 8)], settings={"random_pick_mode": False})
    bundle = await build_bundle("u1", "lang1", api)

    positions = [u["card_front"]["meta"]["session_pos"] for u in bundle["words"]]
    assert positions == list(range(1, len(bundle["words"]) + 1)), positions
    assert len(set(positions)) == len(positions), "session_pos must be unique per unit"

    # The answer side must agree with the question side for the same word.
    for unit in bundle["words"]:
        assert unit["card_answer"]["meta"]["session_pos"] == unit["card_front"]["meta"]["session_pos"]

    # word_number keeps coming from the word itself and must stay distinct too.
    numbers = [u["word_number"] for u in bundle["words"]]
    assert len(set(numbers)) == len(numbers)


@pytest.mark.asyncio
async def test_build_bundle_respects_limit():
    api = make_mock_api(words=[make_word(i) for i in range(1, 11)], settings={"random_pick_mode": False})
    bundle = await build_bundle("u1", "lang1", api, limit=4)
    assert len(bundle["words"]) == 4


@pytest.mark.asyncio
async def test_build_bundle_does_not_clobber_active_session():
    """A background prefetch must not disturb the user's active online session."""
    api = make_mock_api(words=[make_word(i) for i in range(1, 4)], settings={"random_pick_mode": False})
    active = await start_session("u_clobber", "lang1", api)  # registered
    active_id = active["session_id"]
    assert get_session("u_clobber", "lang1")["session_id"] == active_id

    await build_bundle("u_clobber", "lang1", api)

    still = get_session("u_clobber", "lang1")
    assert still is not None
    assert still["session_id"] == active_id, "bundle prefetch clobbered the active session"


# ── apply_results_batch ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_apply_results_batch_validation_ok_and_idempotency():
    session_service._processed_event_ids.clear()
    api = make_mock_api(settings={})
    events = [
        {"event_id": "e-empty", "word_id": "", "rating": "know", "ts": "001"},
        {"event_id": "e-badrate", "word_id": "word-1", "rating": "maybe", "ts": "002"},
        {"event_id": "e-ok", "word_id": "word-1", "rating": "know", "ts": "003"},
        {"event_id": "e-skip", "word_id": "word-2", "rating": "skip", "ts": "004"},
    ]
    res = await apply_results_batch("u1", "lang1", events, api)
    acks = {a["event_id"]: a["status"] for a in res["acks"]}
    assert acks["e-empty"] == "invalid"
    assert acks["e-badrate"] == "invalid"
    assert acks["e-ok"] == "ok"
    assert acks["e-skip"] == "ok"

    # Re-posting the same batch: previously-applied events come back as duplicates.
    res2 = await apply_results_batch("u1", "lang1", events, api)
    acks2 = {a["event_id"]: a["status"] for a in res2["acks"]}
    assert acks2["e-ok"] == "duplicate"
    assert acks2["e-skip"] == "duplicate"
    # Invalid events are never marked processed → still invalid on repost.
    assert acks2["e-empty"] == "invalid"
    assert acks2["e-badrate"] == "invalid"


@pytest.mark.asyncio
async def test_apply_results_batch_applies_in_timestamp_order():
    session_service._processed_event_ids.clear()
    api = make_mock_api(settings={})
    seen = []

    async def spy_get_user_word_data(user_id, word_id):
        seen.append(word_id)
        return {"success": True, "result": None}

    api.get_user_word_data.side_effect = spy_get_user_word_data
    # Deliberately out of order; must be applied by ts ascending.
    events = [
        {"event_id": "b", "word_id": "word-2", "rating": "know", "ts": "020"},
        {"event_id": "a", "word_id": "word-1", "rating": "know", "ts": "010"},
        {"event_id": "c", "word_id": "word-3", "rating": "know", "ts": "030"},
    ]
    await apply_results_batch("u1", "lang1", events, api)
    # update_word_score reads each word more than once; collapse consecutive
    # duplicates and assert the words were processed in ascending-ts order.
    ordered = [w for i, w in enumerate(seen) if i == 0 or w != seen[i - 1]]
    assert ordered == ["word-1", "word-2", "word-3"]

# ── что зависит от нажатия, в снимок не попадает ─────────────────────────────

@pytest.mark.asyncio
async def test_prerendered_answer_card_has_no_you_knew_it_badge():
    """
    Плашка «⏱ Вы знали это слово» держится на score_changed — то есть на том,
    ЧТО пользователь нажал. В партии ответная сторона рисуется заранее, одна на
    оба исхода, и score_changed там всегда False: плашка вылезала и после
    «Знаю», где онлайн её прячет. Офлайн сообщал о провале, которого не было.
    """
    word = make_word(1)
    word["user_word_data"] = {"score": 1, "check_interval": 5, "is_skipped": False}
    api = make_mock_api(words=[word], settings={"random_pick_mode": False})

    bundle = await build_bundle("u_badge", "lang1", api)
    answer = bundle["words"][0]["card_answer"]

    notices = [c["text"] for c in answer["content"] if c["type"] == "notice"]
    assert not any("Вы знали это слово" in n for n in notices), notices


@pytest.mark.asyncio
async def test_online_answer_card_still_shows_it_after_a_failure():
    """Контроль: онлайн плашка обязана остаться — она отмечает откат."""
    from app.services.card_builder import build_card

    word = make_word(1)
    word["user_word_data"] = {"score": 1, "check_interval": 5, "is_skipped": False}
    session = {"settings": {}, "words": [], "current_index": 0, "score_changed": False}

    card = build_card(session, word, show_answer=True)
    notices = [c["text"] for c in card["content"] if c["type"] == "notice"]
    assert any("Вы знали это слово" in n for n in notices), notices

