"""
Batch results endpoint — applies study results accumulated offline (Android outbox).
"""
from typing import List
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.services import session_service
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
async def results_batch(req: ResultsBatchRequest, api_client=Depends(get_api_client)):
    events = [e.model_dump() for e in req.events]
    return await session_service.apply_results_batch(
        req.user_id, req.language_id, events, api_client
    )
