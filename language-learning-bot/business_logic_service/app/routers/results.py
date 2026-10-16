"""
Batch results endpoint — applies study results accumulated offline (Android outbox).
"""
from typing import List
from fastapi import APIRouter, BackgroundTasks, Depends
from pydantic import BaseModel

from app.services import session_service, statistics_service
from app.api.client import get_api_client

router = APIRouter(prefix="/results", tags=["results"])


class ResultEvent(BaseModel):
    event_id: str
    word_id: str
    rating: str          # know | dont_know | skip
    ts: str = ""


class ResultsBatchRequest(BaseModel):
    user_id: str
    language_id: str
    events: List[ResultEvent]


@router.post("/batch")
async def results_batch(req: ResultsBatchRequest,
                        background_tasks: BackgroundTasks,
                        api_client=Depends(get_api_client)):
    """
    Применить накопленное офлайн — и записать это в статистику.

    Про статистику здесь долго не было ни слова: дневной снимок, максимум
    пройденного номера, подогрев графиков и «первый финиш» делал только
    онлайн-путь. Для человека, который занимается в метро, занятия просто не
    существовали: у владельца «первый финиш» перестал записываться 20.09, и на
    графике за месяц осталось четыре точки.

    Фоном, а не в ответе: телефон ждёт подтверждения о своих ответах, а не
    пересчёта статистики, и задерживать его на это незачем.
    """
    events = [e.model_dump() for e in req.events]
    result = await session_service.apply_results_batch(
        req.user_id, req.language_id, events, api_client
    )
    applied = any(a.get("status") == "ok" for a in result.get("acks", []))
    if applied:
        background_tasks.add_task(
            statistics_service.after_answers_applied,
            req.user_id, req.language_id, api_client)
        background_tasks.add_task(
            statistics_service.write_first_finish_if_day_is_done,
            req.user_id, req.language_id, api_client)
    return result
