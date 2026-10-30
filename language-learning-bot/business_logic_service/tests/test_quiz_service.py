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



# ── сколько вариантов на экране ───────────────────────────────────────────────

@pytest.mark.asyncio
async def test_setting_counts_buttons_not_distractors():
    """
    Настройка подписана «Вариантов в режиме выбора» и означает столько кнопок,
    сколько человек увидит. Раньше она бралась как число отвлекающих, и при «5»
    на экране выходило шесть.
    """
    current = make_word("w1", "hello", "привет", word_number=9)
    pool = [make_word(f"w{i}", f"f{i}", f"перевод{i}", word_number=i) for i in range(1, 9)]
    settings = {"quiz_options_count": 5, "random_transcription": False, "random_sound": False}
    session = make_session(words_studied=20, show_mode="foreign", settings=settings)

    result = await generate_quiz_options(session, current, make_api_client(pool))
    assert len(result["options"]) == 5, [o["target_text"] for o in result["options"]]
    assert sum(1 for o in result["options"] if o["is_correct"]) == 1


@pytest.mark.asyncio
async def test_translation_options_are_not_filtered_by_word_count():
    """
    Фильтр по числу единиц оправдан, когда варианты — слово или транскрипция:
    там длина ответа видна и по ней можно угадать. У вариантов-переводов такого
    признака нет, а фильтр резал выбор до нескольких кандидатов.

    Здесь у правильного ответа перевод из четырёх слов, а у всех отвлекающих —
    из одного, и все они обязаны дойти до экрана.

    show_mode="foreign" выбран ради однозначности: при отключённых транскрипции
    и звуке остаётся единственная возможная модальность ответа — перевод. С
    show_mode="transcription" она выбиралась случайно между переводом и словом,
    и тест падал через раз.
    """
    current = make_word("w1", "hayiti", "я был, я была", word_number=9)
    pool = [make_word(f"w{i}", f"f{i}", f"слово{i}", word_number=i) for i in range(1, 9)]
    settings = {"quiz_options_count": 5, "random_transcription": False, "random_sound": False}
    session = make_session(words_studied=20, show_mode="foreign", settings=settings)
    api = make_api_client(pool)

    result = await generate_quiz_options(session, current, api)
    assert result["target_modality"] == "translation"
    assert len(result["options"]) == 5, [o["target_text"] for o in result["options"]]
    # Однозначный признак, что фильтр не включался: запрос слов по числу единиц
    # делается только под ним.
    api.get_words_by_unit_count.assert_not_called()


@pytest.mark.asyncio
async def test_short_pool_is_topped_up_instead_of_silently_shrinking():
    """
    Когда фильтр не набирает нужного числа, добираем без него. Раньше добор шёл
    только при падении ниже половины: три отвлекающих из пяти считались
    достаточными, и человек молча получал меньше кнопок, чем просил.
    """
    # Правильный ответ из двух единиц, отвлекающие — из одной: фильтр по числу
    # единиц отсеет всех, и добор обязан вернуть их обратно.
    current = make_word("w1", "два слова", "перевод", word_number=9)
    pool = [make_word(f"w{i}", f"одно{i}", f"перевод{i}", word_number=i) for i in range(1, 9)]
    settings = {"quiz_options_count": 5, "random_transcription": False, "random_sound": False}
    session = make_session(words_studied=20, show_mode="translation", settings=settings)

    result = await generate_quiz_options(session, current, make_api_client(pool))
    assert result["target_modality"] == "foreign"
    assert len(result["options"]) == 5, [o["target_text"] for o in result["options"]]


@pytest.mark.asyncio
async def test_two_is_the_floor():
    """Меньше двух кнопок выбор не выбор — даже если в настройке единица."""
    current = make_word("w1", "hello", "привет", word_number=9)
    pool = [make_word(f"w{i}", f"f{i}", f"перевод{i}", word_number=i) for i in range(1, 9)]
    settings = {"quiz_options_count": 1, "random_transcription": False, "random_sound": False}
    session = make_session(words_studied=20, show_mode="foreign", settings=settings)

    result = await generate_quiz_options(session, current, make_api_client(pool))
    assert len(result["options"]) == 2


# ── синонимы не идут в отвлекающие ───────────────────────────────────────────

def test_meanings_are_split_and_stripped_of_notes():
    """
    Уточнение в скобках — не значение. Из-за него два синонима выглядели
    разными строками и спокойно становились вариантами одного вопроса.
    """
    from app.services.quiz_service import meanings_of
    assert meanings_of("здесь, тут (чаще на письме)") == {"здесь", "тут"}
    assert meanings_of("здесь, тут (чаще в речи)") == {"здесь", "тут"}
    assert meanings_of("хватит, довольно; достаточно") == {"хватит", "довольно", "достаточно"}


def test_a_homograph_note_does_not_leak_into_meanings():
    """У омографов перевод многострочный; вторая строка — пометка, не значение."""
    from app.services.quiz_service import meanings_of
    assert meanings_of("здесь\n⚠ то же написание читается иначе: рот") == {"здесь"}


@pytest.mark.asyncio
async def test_a_synonym_is_never_offered_as_a_distractor():
    """
    Жалоба владельца: «слово 101, в пик-режиме кажется выбрал правильное, но
    ответ не принят — либо ошибка, либо два слова очень похожих».

    Похожих: 35 כָּאן «здесь, тут (чаще на письме)» и 101 פֹּה «здесь, тут
    (чаще в речи)». Оба значат «здесь», и по вопросу не понять, о каком речь.
    Отвлекающие отсеивались по совпадению показанного ТЕКСТА — а тексты у них
    разные, и на иврите тем более.
    """
    current = make_word("w101", "פֹּה", "здесь, тут (чаще в речи)", word_number=101)
    distractors = [
        make_word("w35", "כָּאן", "здесь, тут (чаще на письме)", word_number=35),
        make_word("w7", "כֶּלֶב", "собака", word_number=7),
    ]
    settings = {"quiz_options_count": 2, "random_transcription": False, "random_sound": False}
    session = make_session(words_studied=200, show_mode="foreign", settings=settings)

    result = await generate_quiz_options(session, current, make_api_client(distractors))

    assert result is not None
    ids = [o["word_id"] for o in result["options"]]
    assert "w35" not in ids, f"синоним предложен вариантом: {result['options']}"
    assert "w101" in ids


@pytest.mark.asyncio
async def test_the_synonym_rule_works_when_the_word_itself_is_shown():
    """
    Самый злой случай: показывают не перевод, а само слово. Тексты вариантов
    тогда различаются всегда, и прежняя защита по тексту не срабатывала вовсе.
    """
    current = make_word("w101", "פֹּה", "здесь, тут (чаще в речи)", word_number=101)
    distractors = [make_word("w35", "כָּאן", "здесь, тут (чаще на письме)", word_number=35)]
    settings = {"quiz_options_count": 2, "random_transcription": False, "random_sound": False}
    session = make_session(words_studied=200, show_mode="translation", settings=settings)

    result = await generate_quiz_options(session, current, make_api_client(distractors))

    # Единственный кандидат — синоним, поэтому вопроса не выходит вовсе.
    # Это честнее, чем вопрос с двумя верными ответами.
    assert result is None or all(
        o["word_id"] != "w35" for o in result["options"]), result


@pytest.mark.asyncio
async def test_a_different_word_is_still_a_good_distractor():
    """Опора: обычные слова отсеиваться не должны."""
    current = make_word("w1", "פֹּה", "здесь", word_number=101)
    distractors = [
        make_word("w2", "כֶּלֶב", "собака", word_number=7),
        make_word("w3", "בַּיִת", "дом", word_number=8),
    ]
    settings = {"quiz_options_count": 2, "random_transcription": False, "random_sound": False}
    session = make_session(words_studied=200, show_mode="foreign", settings=settings)

    result = await generate_quiz_options(session, current, make_api_client(distractors))

    assert result is not None
    ids = {o["word_id"] for o in result["options"]}
    assert ids & {"w2", "w3"}, f"отвлекающие пропали вовсе: {result['options']}"
