"""
История рассылок: что сохраняется и в каком порядке.

Проверяется на настоящей MongoDB во временной базе — боевая не задействована
ни на чтение. Подделкой коллекции тут проверять нечего: сортировка и выборка
выполняются базой, и фальшивка проверяла бы мою же копию её поведения.

Повод: 08.11.2026 владелец отправил четыре сообщения, и восстановить их тексты
было уже неоткуда. Рассылка уходила в телеграм и нигде не оставалась.
"""
import os
import sys
import uuid
from datetime import datetime, timedelta

import pytest
import pytest_asyncio

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from app.db.repositories.broadcast_repository import BroadcastRepository  # noqa: E402

MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://localhost:8527")


@pytest_asyncio.fixture
async def repo():
    from motor.motor_asyncio import AsyncIOMotorClient
    try:
        cl = AsyncIOMotorClient(MONGODB_URL, serverSelectionTimeoutMS=1500)
        await cl.admin.command("ping")
    except Exception as e:                                  # pragma: no cover
        pytest.skip(f"MongoDB недоступна ({e})")

    имя = f"langbot_test_broadcasts_{uuid.uuid4().hex[:8]}"
    assert "language_learning_bot" not in имя
    try:
        yield BroadcastRepository(cl[имя])
    finally:
        await cl.drop_database(имя)
        cl.close()


@pytest.mark.asyncio
async def test_отправленное_сохраняется_целиком(repo):
    await repo.add({
        "text": "вышла версия 6",
        "sent_by": "admin-1",
        "recipient": "all",
        "recipient_name": "всем",
        "language_id": "any",
        "language_name": "независимо от языка",
        "sent_count": 3,
        "skipped": [],
        "errors": [],
    })

    записи = await repo.recent()
    assert len(записи) == 1
    з = записи[0]
    assert з["text"] == "вышла версия 6"
    assert з["sent_count"] == 3
    assert з["recipient_name"] == "всем"
    assert з["id"], "у записи нет идентификатора"


@pytest.mark.asyncio
async def test_время_проставляется_само(repo):
    """Без времени история бесполезна: непонятно, что когда уходило."""
    до = datetime.utcnow() - timedelta(seconds=5)
    await repo.add({"text": "привет", "sent_count": 1})
    з = (await repo.recent())[0]
    assert з["sent_at"] >= до


@pytest.mark.asyncio
async def test_новые_сверху(repo):
    """Смотреть историю начинают с последнего отправленного."""
    сейчас = datetime.utcnow()
    for n, сдвиг in ((1, 3), (2, 2), (3, 1)):
        await repo.add({"text": f"письмо {n}", "sent_count": n,
                        "sent_at": сейчас - timedelta(hours=сдвиг)})

    тексты = [з["text"] for з in await repo.recent()]
    assert тексты == ["письмо 3", "письмо 2", "письмо 1"], тексты


@pytest.mark.asyncio
async def test_пропуски_и_ошибки_сохраняются(repo):
    """
    Главное в записи — не только текст. «Отправлено 0» выглядит поломкой, а
    причина — отказ человека от сообщений — видна только в пропусках.
    """
    await repo.add({
        "text": "текст", "sent_count": 0,
        "skipped": ["Юрий — выключено «Получать сообщения» для этого языка"],
        "errors": ["Пётр → chat not found"],
    })

    з = (await repo.recent())[0]
    assert з["skipped"] and "Юрий" in з["skipped"][0]
    assert з["errors"] and "chat not found" in з["errors"][0]


@pytest.mark.asyncio
async def test_предел_выборки_соблюдается(repo):
    for n in range(7):
        await repo.add({"text": f"п{n}", "sent_count": 1})
    assert len(await repo.recent(limit=3)) == 3
    assert len(await repo.recent()) == 7


@pytest.mark.asyncio
async def test_пустая_история_это_пустой_список_а_не_ошибка(repo):
    assert await repo.recent() == []
    assert await repo.count() == 0
