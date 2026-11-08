"""
API истории рассылок.

Рассылку отправляет веб-админка, но хранить её сама она не может и не должна:
прямого доступа к базе у неё нет, всё идёт через BLS и этот сервис.
"""
from typing import Any, Dict, List

from fastapi import APIRouter, Body, Depends, Query

from app.core.dependencies import get_broadcast_repository
from app.db.repositories.broadcast_repository import BroadcastRepository
from app.utils.logger import setup_logger

router = APIRouter(prefix="/broadcasts", tags=["broadcasts"])
logger = setup_logger(__name__)


@router.post("")
async def add_broadcast(
    запись: Dict[str, Any] = Body(...),
    repo: BroadcastRepository = Depends(get_broadcast_repository),
):
    """Сохранить отправленную рассылку."""
    идентификатор = await repo.add(запись)
    logger.info(f"Сохранена рассылка {идентификатор}, "
                f"отправлено {запись.get('sent_count')}")
    return {"id": идентификатор}


@router.get("")
async def list_broadcasts(
    limit: int = Query(50, ge=1, le=500),
    repo: BroadcastRepository = Depends(get_broadcast_repository),
) -> List[Dict[str, Any]]:
    """Последние рассылки, новые сверху."""
    return await repo.recent(limit)
