"""
«Сегодняшняя порция пройдена» — счётчик, по которому записывается первый финиш.

Жалоба владельца: на графике «не знал на первом проходе» четыре точки за месяц,
и после обновления их по-прежнему четыре.

Разбор. Признаком финиша было «слов на сегодня больше нет», а это не наступает
никогда: ответ «не знаю» переносит срок проверки на сегодня, слово возвращается
в тот же день, и счётчик «на сегодня» не доходит до нуля, пока человек не
выучит всё до последнего слова. До того признаком был конец партии сессии — но
партия это сто слов (повторы плюс новые), а в день проходится 25–60, и
кончаться она перестала. Последняя запись — 20.09.2026.

Теперь порция считается по данным: назначенные НА сегодня повторы, и каждое
различается по тому, был ли ответ в этих сутках (updated_at). Повторы того же
дня — второй проход, в порцию не входят.

Проверяется на настоящей агрегации в отдельной временной базе. Подделкой
коллекции такое не проверить: все условия живут в выражениях MongoDB, и фальшивка
проверяла бы мою же переписанную их копию, а не то, что выполнит база.
"""

import os
import sys
import uuid
from datetime import datetime, timedelta

import pytest
import pytest_asyncio
from bson import ObjectId

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))

from app.db.repositories.statistics_repository import StatisticsRepository  # noqa: E402

MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://localhost:8527")
USER = str(ObjectId())
LANG = str(ObjectId())
TZ, DAY_START_HOUR = "Europe/Moscow", 4


async def _client():
    from motor.motor_asyncio import AsyncIOMotorClient
    cl = AsyncIOMotorClient(MONGODB_URL, serverSelectionTimeoutMS=1500)
    await cl.admin.command("ping")
    return cl


@pytest_asyncio.fixture
async def repo():
    """Своя база на каждый прогон; боевая не задействована ни на чтение."""
    try:
        cl = await _client()
    except Exception as e:                                  # pragma: no cover
        pytest.skip(f"MongoDB недоступна ({e}) — проверка агрегации пропущена")
    name = f"langbot_test_portion_{uuid.uuid4().hex[:8]}"
    assert "language_learning_bot" not in name
    db = cl[name]
    await db.user_language_settings.insert_one({
        "user_id": ObjectId(USER), "language_id": ObjectId(LANG),
        "timezone": TZ, "day_start_hour": DAY_START_HOUR,
    })
    try:
        yield StatisticsRepository(db)
    finally:
        await cl.drop_database(name)
        cl.close()


async def _day_start(repo) -> datetime:
    _, today = await repo._day_bounds(USER, LANG)
    return today


async def add_word(repo, *, next_check_date, updated_at, created_at=None,
                   score=0, is_skipped=False):
    """Слово со статистикой; слово обязано существовать — агрегация их сверяет."""
    word_id = ObjectId()
    await repo.db.words.insert_one({
        "_id": word_id, "language_id": ObjectId(LANG),
        "word_number": await repo.db.words.count_documents({}) + 1,
        "word_foreign": "x", "translation": "х",
    })
    await repo.collection.insert_one({
        "user_id": USER, "language_id": LANG, "word_id": str(word_id),
        "score": score, "is_skipped": is_skipped, "check_interval": 1,
        "next_check_date": next_check_date,
        "created_at": created_at or (updated_at - timedelta(days=30)),
        "updated_at": updated_at,
    })


async def counts(repo) -> dict:
    return await repo.count_user_statistics_by_conditions(
        user_id=USER, language_id=LANG, validate_words=True)


@pytest.mark.asyncio
async def test_a_word_due_today_and_not_yet_answered_keeps_the_portion_open(repo):
    start = await _day_start(repo)
    await add_word(repo, next_check_date=start - timedelta(days=1),
                   updated_at=start - timedelta(days=2))
    c = await counts(repo)
    assert c["words_portion_left"] == 1
    assert c["words_answered_today"] == 0


@pytest.mark.asyncio
async def test_answering_it_today_closes_the_portion(repo):
    """Ответ в этих сутках — слово из порции пройдено."""
    start = await _day_start(repo)
    await add_word(repo, next_check_date=start - timedelta(days=1),
                   updated_at=start + timedelta(hours=3))
    c = await counts(repo)
    assert c["words_portion_left"] == 0
    assert c["words_answered_today"] == 1


@pytest.mark.asyncio
async def test_a_repeat_of_the_same_day_does_not_reopen_the_portion(repo):
    """
    Сторож против прежнего признака. «Не знаю» переносит срок на сегодня —
    слово снова «на сегодня», и по старому условию («слов на сегодня нет»)
    финиш не наступал никогда. Порция при этом пройдена.
    """
    start = await _day_start(repo)
    await add_word(repo, next_check_date=start,                  # вернулось на сегодня
                   updated_at=start + timedelta(hours=5),        # ответ был сегодня
                   score=0)
    c = await counts(repo)
    assert c["words_for_today"] >= 1, "слово действительно снова ждёт на сегодня"
    assert c["words_portion_left"] == 0, "повтор того же дня держит порцию открытой"
    assert c["words_answered_today"] == 1


@pytest.mark.asyncio
async def test_a_new_word_taken_today_does_not_create_a_portion(repo):
    """
    Новое слово, впервые взятое сегодня, порции не создаёт — порция это
    назначенные повторы. Но как занятие оно считается: человек работал.
    """
    start = await _day_start(repo)
    await add_word(repo, next_check_date=start, updated_at=start + timedelta(hours=2),
                   created_at=start + timedelta(hours=2))
    c = await counts(repo)
    assert c["words_portion_left"] == 0
    assert c["words_answered_today"] == 1


@pytest.mark.asyncio
async def test_a_word_answered_known_today_still_counts_as_work(repo):
    """
    Сторож против моей же первой попытки. Сначала вторым счётчиком было
    «сколько порции пройдено» — но слово, отвеченное «знаю», получает срок в
    будущем и из порции исчезает. В день, когда человек знал все повторы, тот
    счётчик показал бы ноль, это прочлось бы как «порции не было», и финиш не
    записался бы именно в самый удачный день.
    """
    start = await _day_start(repo)
    await add_word(repo, next_check_date=start + timedelta(days=4),   # уехало в будущее
                   updated_at=start + timedelta(hours=3),            # отвечено сегодня
                   created_at=start - timedelta(days=20), score=1)
    c = await counts(repo)
    assert c["words_portion_left"] == 0
    assert c["words_answered_today"] == 1, "ответ «знаю» не зачтён за занятие"


@pytest.mark.asyncio
async def test_a_skipped_word_does_not_hold_the_portion_forever(repo):
    """Помеченное «пропустить» на занятии не выдают — ждать его нельзя."""
    start = await _day_start(repo)
    await add_word(repo, next_check_date=start - timedelta(days=5),
                   updated_at=start - timedelta(days=5), is_skipped=True)
    c = await counts(repo)
    assert c["words_portion_left"] == 0


@pytest.mark.asyncio
async def test_a_word_due_later_is_not_in_the_portion(repo):
    start = await _day_start(repo)
    await add_word(repo, next_check_date=start + timedelta(days=3),
                   updated_at=start - timedelta(hours=1), score=1)
    c = await counts(repo)
    assert c["words_portion_left"] == 0
    assert c["words_answered_today"] == 0


@pytest.mark.asyncio
async def test_the_day_of_the_owner_is_counted_by_his_own_boundary(repo):
    """
    Сутки у человека свои: Europe/Moscow и начало в 4 утра — это 01:00 UTC.
    Ответ, данный в 02:00 UTC, относится к сегодняшним суткам, а в 00:30 — к
    прошедшим, и такое слово порцию не закрывает.
    """
    start = await _day_start(repo)
    assert start.hour == 1, f"граница суток не по настройкам: {start}"
    await add_word(repo, next_check_date=start - timedelta(days=1),
                   updated_at=start - timedelta(minutes=30))
    c = await counts(repo)
    assert c["words_portion_left"] == 1, "ответ до границы зачтён за сегодняшний"


@pytest.mark.asyncio
async def test_a_mixed_day_counts_only_what_is_left(repo):
    """Разом: три повтора, два пройдены — порция ещё открыта."""
    start = await _day_start(repo)
    for hours in (2, 6):
        await add_word(repo, next_check_date=start - timedelta(days=1),
                       updated_at=start + timedelta(hours=hours))
    await add_word(repo, next_check_date=start - timedelta(days=1),
                   updated_at=start - timedelta(days=1))
    c = await counts(repo)
    assert (c["words_portion_left"], c["words_answered_today"]) == (1, 2)


@pytest.mark.asyncio
async def test_the_light_answer_carries_three_numbers_and_no_lists(repo):
    """
    Лёгкая ручка нужна потому, что признак спрашивается на каждый ответ.
    Если в ответ просочатся массивы номеров слов, смысл её исчезнет — а
    просочиться им легко: они собираются той же агрегацией.
    """
    start = await _day_start(repo)
    await add_word(repo, next_check_date=start - timedelta(days=1),
                   updated_at=start + timedelta(hours=1))
    await add_word(repo, next_check_date=start - timedelta(days=1),
                   updated_at=start - timedelta(days=1))

    state = await repo.get_portion_state(USER, LANG)
    assert set(state) == {"words_portion_left", "words_answered_today", "words_unknown_now"}
    assert state["words_portion_left"] == 1
    assert state["words_answered_today"] == 1

    raw = await repo.count_user_statistics_by_conditions(
        user_id=USER, language_id=LANG, validate_words=True, with_lists=False)
    for heavy in ("word_numbers_for_today", "word_numbers_unknown", "word_check_interval"):
        assert heavy not in raw, f"{heavy} остался в лёгком ответе"


@pytest.mark.asyncio
async def test_the_full_answer_still_carries_the_lists(repo):
    """Опора: обычный вызов прогресса не должен потерять свои списки."""
    start = await _day_start(repo)
    await add_word(repo, next_check_date=start - timedelta(days=1),
                   updated_at=start + timedelta(hours=1), score=0)
    full = await repo.count_user_statistics_by_conditions(
        user_id=USER, language_id=LANG, validate_words=True)
    assert full["word_numbers_unknown"], "список незнакомых опустел"
    assert full["word_numbers_for_today"]
    assert full["word_check_interval"]


@pytest.mark.asyncio
async def test_an_empty_base_answers_zeroes_not_an_error(repo):
    """Ничего не изучено — ручку всё равно зовут на каждый ответ."""
    state = await repo.get_portion_state(USER, LANG)
    assert state == {"words_portion_left": 0, "words_answered_today": 0,
                     "words_unknown_now": 0}
