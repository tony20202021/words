"""
Повторения, отсечённые настройкой «начальный номер слова».

Жалоба владельца про пользователя Yuri: «кажется, он не перестартует сессии
для повторения, а вместо этого ставит в настройках каждый раз больше номер
слова». Проверка по базе 07.11.2026 показала, что прыжков нет — он идёт ровно,
по ~440 слов на каждые 500 номеров. Зато у него start_word = 3000, и вот что
это значило:

    1–1000     904 слова, ждут повторения 904
 1001–2000     890 слов,  ждут повторения 890
 2001–3000     887 слов,  ждут повторения 752

2546 слов ждали повторения и не показались бы никогда. В диапазоне 1–2000
просрочено было всё до единого слова.

Причина в отборе: statistics_service.get_words_for_study фильтрует
word_number >= start_word для ВСЕХ слов сразу, включая пришедшие на
повторение. Настройка называется «начальный номер слова», и человек, поднимая
её, чтобы идти дальше, молча терял повторения всего пройденного.

Решение владельца: поведение отбора оставить, но СКАЗАТЬ. Здесь проверяется
само число — то, которое экран покажет.

Проверяется на настоящей агрегации во временной базе: все условия живут в
выражениях MongoDB, и подделка коллекции проверяла бы мою же переписанную их
копию, а не то, что выполнит база.
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


async def _client():
    from motor.motor_asyncio import AsyncIOMotorClient
    cl = AsyncIOMotorClient(MONGODB_URL, serverSelectionTimeoutMS=1500)
    await cl.admin.command("ping")
    return cl


@pytest_asyncio.fixture
async def make_repo():
    """Фабрика: порог задаётся на каждый случай свой."""
    try:
        cl = await _client()
    except Exception as e:                                  # pragma: no cover
        pytest.skip(f"MongoDB недоступна ({e}) — проверка агрегации пропущена")
    name = f"langbot_test_startword_{uuid.uuid4().hex[:8]}"
    assert "language_learning_bot" not in name
    db = cl[name]

    async def make(start_word=None):
        doc = {"user_id": ObjectId(USER), "language_id": ObjectId(LANG),
               "timezone": "UTC", "day_start_hour": 0}
        if start_word is not None:
            doc["start_word"] = start_word
        await db.user_language_settings.delete_many({})
        await db.user_language_settings.insert_one(doc)
        return StatisticsRepository(db)

    try:
        yield make
    finally:
        await cl.drop_database(name)
        cl.close()


async def add_word(repo, number, *, due, is_skipped=False):
    """Слово с заданным номером; просроченное или нет."""
    word_id = ObjectId()
    await repo.db.words.insert_one({
        "_id": word_id, "language_id": ObjectId(LANG), "word_number": number,
        "word_foreign": "x", "translation": "х",
    })
    когда = (datetime.utcnow() - timedelta(days=1) if due
             else datetime.utcnow() + timedelta(days=10))
    await repo.collection.insert_one({
        "user_id": USER, "language_id": LANG, "word_id": str(word_id),
        "score": 1, "is_skipped": is_skipped, "check_interval": 4,
        "next_check_date": когда,
        "created_at": datetime.utcnow() - timedelta(days=30),
        "updated_at": datetime.utcnow() - timedelta(days=5),
    })


async def counts(repo):
    return await repo.count_user_statistics_by_conditions(
        user_id=USER, language_id=LANG, validate_words=True)


@pytest.mark.asyncio
async def test_words_due_below_the_threshold_are_counted(make_repo):
    """Главное число: сколько повторений человек не увидит."""
    repo = await make_repo(start_word=3000)
    await add_word(repo, 100, due=True)
    await add_word(repo, 2999, due=True)
    await add_word(repo, 3001, due=True)       # выше порога — покажется

    c = await counts(repo)
    assert c["words_hidden_by_start_word"] == 2, c
    assert c["start_word"] == 3000


@pytest.mark.asyncio
async def test_a_word_not_due_yet_is_not_counted(make_repo):
    """Считаются только те, которым УЖЕ пора: остальные никто и не ждёт."""
    repo = await make_repo(start_word=3000)
    await add_word(repo, 100, due=False)

    assert (await counts(repo))["words_hidden_by_start_word"] == 0


@pytest.mark.asyncio
async def test_a_skipped_word_is_not_counted(make_repo):
    """Помеченные пропущенными не выдаются и так — их потеря не новость."""
    repo = await make_repo(start_word=3000)
    await add_word(repo, 100, due=True, is_skipped=True)

    assert (await counts(repo))["words_hidden_by_start_word"] == 0


@pytest.mark.asyncio
async def test_without_a_threshold_nothing_is_hidden(make_repo):
    """
    Опора: у кого порог не трогали, строка на экране не должна появляться
    вовсе. Иначе предупреждение станет фоном, который перестают читать.
    """
    repo = await make_repo(start_word=1)
    await add_word(repo, 1, due=True)
    await add_word(repo, 5000, due=True)

    c = await counts(repo)
    assert c["words_hidden_by_start_word"] == 0
    assert c["start_word"] == 1


@pytest.mark.asyncio
async def test_a_missing_setting_means_no_threshold(make_repo):
    """Настройки может не быть вовсе — это «порога нет», а не «порог ноль»."""
    repo = await make_repo(start_word=None)
    await add_word(repo, 7, due=True)

    c = await counts(repo)
    assert c["start_word"] == 1
    assert c["words_hidden_by_start_word"] == 0
