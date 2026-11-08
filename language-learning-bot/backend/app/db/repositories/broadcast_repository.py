"""
Хранение истории рассылок.

Зачем. Рассылка уходит людям в телеграм и нигде не остаётся: 08.11.2026
владелец отправил четыре сообщения, и восстановить их тексты было уже неоткуда
— разве что попросить получателя показать переписку. Непонятно и кому что
дошло: отчёт об отправке живёт одну страницу и исчезает с перезагрузкой.

Что хранится. Текст, время, кто отправил, кому предназначалось (всем или
одному, по языку или независимо) и чем кончилось: сколько ушло, кого пропустила
настройка «Получать сообщения», какие были ошибки. Пропуски важны не меньше
отправок: «отправлено 0» без объяснения выглядит поломкой, хотя человек просто
отказался от сообщений.
"""
from datetime import datetime
from typing import Any, Dict, List

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.utils.logger import setup_logger

logger = setup_logger(__name__)


class BroadcastRepository:
    """Записи об отправленных рассылках."""

    def __init__(self, database: AsyncIOMotorDatabase):
        self.db = database
        self.collection = database["broadcasts"]

    async def add(self, запись: Dict[str, Any]) -> str:
        """Сохраняет одну рассылку, возвращает её идентификатор."""
        запись = dict(запись)
        запись.setdefault("sent_at", datetime.utcnow())
        итог = await self.collection.insert_one(запись)
        return str(итог.inserted_id)

    async def recent(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Последние рассылки, новые сверху."""
        курсор = self.collection.find().sort("sent_at", -1).limit(max(1, limit))
        out = []
        async for d in курсор:
            d["id"] = str(d.pop("_id"))
            out.append(d)
        return out

    async def count(self) -> int:
        return await self.collection.count_documents({})
