"""Tests for quiz_service: weighted sampling, text extraction, option generation."""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock
from app.services.quiz_service import (
    _weighted_sample,
    _get_text_for_modality,
    _choose_target_modality,
    generate_quiz_options,
    PROB_MAX_RATIO,
)


# ── _weighted_sample ──────────────────────────────────────────────────────────

def test_weighted_sample_basic():
    result = _weighted_sample([1, 2, 3, 4, 5], 3, exclude=0)
    assert len(result) == 3
    assert len(set(result)) == 3  # no duplicates


def test_weighted_sample_excludes():
    result = _weighted_sample([1, 2, 3, 4], 3, exclude=2)
    assert 2 not in result


def test_weighted_sample_count_capped_by_pool():
    result = _weighted_sample([1, 2, 3], 10, exclude=0)
    assert len(result) == 3


def test_weighted_sample_empty_pool():
    result = _weighted_sample([1], 3, exclude=1)
    assert result == []


def test_weighted_sample_all_unique():
    for _ in range(20):
        result = _weighted_sample(list(range(1, 20)), 10, exclude=0)
        assert len(result) == len(set(result))


# ── _get_text_for_modality ────────────────────────────────────────────────────

def test_get_text_translation():
    word = {"translation": "  hello  ", "word_foreign": "привет"}
    assert _get_text_for_modality(word, "translation") == "hello"


def test_get_text_foreign():
    word = {"word_foreign": "привет"}
    assert _get_text_for_modality(word, "foreign") == "привет"


def test_get_text_transcription():
    word = {"transcription": "privet"}
    assert _get_text_for_modality(word, "transcription") == "[privet]"


def test_get_text_transcription_empty():
    word = {"transcription": ""}
    assert _get_text_for_modality(word, "transcription") is None


def test_get_text_sound_json():
    sounds = json.dumps({"1": "path/to/sound.mp3"})
    word = {"sounds": sounds}
    assert _get_text_for_modality(word, "sound") == "path/to/sound.mp3"


def test_get_text_sound_none():
    word = {"sounds": None}
    assert _get_text_for_modality(word, "sound") is None


def test_get_text_unknown_modality():
    word = {"translation": "hello"}
    assert _get_text_for_modality(word, "unknown") is None


# ── _choose_target_modality ───────────────────────────────────────────────────

def test_choose_target_different_from_show_mode():
    for _ in range(30):
        result = _choose_target_modality("foreign", {})
        assert result != "foreign"


def test_choose_target_always_in_pool():
    settings = {"random_transcription": True, "random_sound": True, "show_sounds": True}
    valid = {"translation", "foreign", "transcription", "sound"}
    for _ in range(30):
        result = _choose_target_modality("foreign", settings)
        assert result in valid


def test_choose_target_excludes_disabled_transcription():
    settings = {"random_transcription": False, "random_sound": False}
    for _ in range(30):
        result = _choose_target_modality("foreign", settings)
        assert result not in ("transcription", "sound")


# ── generate_quiz_options ─────────────────────────────────────────────────────

def make_word(word_id, word_foreign, translation, word_number, transcription="trnsc"):
    return {
        "_id": word_id,
        "word_number": word_number,
        "word_foreign": word_foreign,
        "translation": translation,
        "transcription": f"{transcription}-{word_id}",
        "sounds": None,
        "user_word_data": {},
    }


def make_session(words_studied=5, show_mode="foreign", settings=None, session_words=None):
    return {
        "session_id": "s1",
        "user_id": "u1",
        "language_id": "lang1",
        "show_mode": show_mode,
        "words_studied": words_studied,
        "settings": settings or {"quiz_options_count": 2},
        "words": session_words or [],
    }


def make_api_client(distractor_words, unit_count_words=None):
    client = MagicMock()
    client.get_words_by_numbers_for_quiz = AsyncMock(
        return_value={"success": True, "result": distractor_words}
    )
    client.get_words_by_unit_count = AsyncMock(
        return_value={"success": True, "result": unit_count_words or []}
    )
    return client


@pytest.mark.asyncio
async def test_generate_quiz_options_returns_options():
    current = make_word("w1", "hello", "привет", word_number=3)
    distractors = [
        make_word("w2", "world", "мир", word_number=1),
        make_word("w3", "cat", "кошка", word_number=2),
    ]
    # Disable sound/transcription so target modality is predictably translation
    settings = {"quiz_options_count": 2, "random_transcription": False, "random_sound": False}
    session = make_session(words_studied=5, show_mode="foreign", settings=settings)
    api = make_api_client(distractors)

    result = await generate_quiz_options(session, current, api)
    assert result is not None
    assert "options" in result
    assert "target_modality" in result
    assert result["target_modality"] == "translation"
    options = result["options"]
    assert len(options) >= 2
    correct = [o for o in options if o["is_correct"]]
    assert len(correct) == 1
    assert correct[0]["word_id"] == "w1"


@pytest.mark.asyncio
async def test_generate_quiz_options_not_enough_words():
    current = make_word("w1", "hello", "привет", word_number=1)
    session = make_session(words_studied=1)
    api = make_api_client([])

    result = await generate_quiz_options(session, current, api)
    assert result is None


@pytest.mark.asyncio
async def test_generate_quiz_options_forbidden_pairs_filtered():
    current = make_word("w1", "hello", "привет", word_number=3)
    current["user_word_data"] = {"forbidden_quiz_pairs": ["w2"]}
    distractors = [
        make_word("w2", "world", "мир", word_number=1),
        make_word("w3", "cat", "кошка", word_number=2),
    ]
    session = make_session(words_studied=5, show_mode="foreign")
    api = make_api_client(distractors)

    result = await generate_quiz_options(session, current, api)
    if result:
        ids = [o["word_id"] for o in result["options"]]
        assert "w2" not in ids


@pytest.mark.asyncio
async def test_generate_quiz_options_api_failure():
    current = make_word("w1", "hello", "привет", word_number=3)
    session = make_session(words_studied=5)
    api = MagicMock()
    api.get_words_by_numbers_for_quiz = AsyncMock(return_value=None)
    api.get_words_by_unit_count = AsyncMock(return_value={"success": True, "result": []})

    result = await generate_quiz_options(session, current, api)
    assert result is None


@pytest.mark.asyncio
async def test_generate_quiz_options_no_valid_distractors():
    current = make_word("w1", "hello", "привет", word_number=3)
    # Distractors have same translation as correct (duplicate text)
    distractors = [
        make_word("w2", "hello2", "привет", word_number=1),  # same translation
    ]
    session = make_session(words_studied=5, show_mode="foreign",
                           settings={"quiz_options_count": 2})
    api = make_api_client(distractors)

    result = await generate_quiz_options(session, current, api)
    # May be None (no valid distractors) or have 1 distractor (with different text skipped)
    # Either way, should not crash
    if result is not None:
        assert len(result["options"]) >= 2

def test_weighted_sample_stays_unique_with_a_boosted_pool():
    """
    Боевой вызов передаёт пул С ПОВТОРАМИ: boosted_pool дублирует нужные номера
    PROB_MAX_RATIO-1 раз, чтобы поднять их вероятность. Выборка идёт без
    повторений, но удалялся выбранный ИНДЕКС, а не значение, так что остальные
    копии оставались и номер мог выпасть снова. Прежний тест этого не видел —
    он проверял пул без повторов.
    """
    from app.services.quiz_service import _weighted_sample, PROB_MAX_RATIO

    pool = list(range(1, 21)) + [3, 7] * (PROB_MAX_RATIO - 1)
    for _ in range(100):
        got = _weighted_sample(pool, 8, exclude=5)
        assert len(got) == len(set(got)), got
        assert len(got) == 8, got
        assert 5 not in got


def test_boost_survives_the_deduplication():
    """Повторы сворачиваются в вес, а не выбрасываются — иначе буст исчез бы."""
    from collections import Counter
    from app.services.quiz_service import _weighted_sample, PROB_MAX_RATIO

    pool = list(range(1, 21)) + [3, 7] * (PROB_MAX_RATIO - 1)
    seen = Counter()
    for _ in range(2000):
        seen.update(_weighted_sample(pool, 4, exclude=5))
    assert seen[3] > seen[2] * 2, (seen[3], seen[2])
    assert seen[7] > seen[8] * 2, (seen[7], seen[8])

