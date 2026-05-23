from fastapi import APIRouter, Depends, HTTPException
from starlette.status import HTTP_404_NOT_FOUND, HTTP_400_BAD_REQUEST
from typing import Optional, Dict, Any
from pydantic import BaseModel
from app.services import session_service
from app.services.card_builder import build_card
from app.api.client import get_api_client

router = APIRouter(prefix="/session", tags=["session"])


class StartSessionRequest(BaseModel):
    user_id: str
    language_id: str
    settings: Optional[Dict[str, Any]] = None


class RateRequest(BaseModel):
    rating: str  # "know" | "dont_know" | "skip"


def _card_response(session: Dict[str, Any]) -> Dict[str, Any]:
    word = session_service.get_current_word(session)
    show_answer = session.get("show_answer", False)
    return {
        "session_id": session["session_id"],
        "card": build_card(session, word, show_answer),
    }


@router.post("/start")
async def start_session(req: StartSessionRequest, api_client=Depends(get_api_client)):
    session = await session_service.start_session(
        req.user_id, req.language_id, api_client, req.settings
    )
    if session is None:
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail="Failed to start session")
    return _card_response(session)


@router.get("/{user_id}/{language_id}")
async def get_session(user_id: str, language_id: str):
    session = session_service.get_session(user_id, language_id)
    if session is None:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="No active session")
    return _card_response(session)


@router.post("/{session_id}/show_answer")
async def show_answer(session_id: str, api_client=Depends(get_api_client)):
    session = session_service.get_session_by_id(session_id)
    if session is None:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="Session not found")
    await session_service.show_answer_word(session, api_client)
    return _card_response(session)


@router.post("/{session_id}/rate")
async def rate_word(session_id: str, req: RateRequest, api_client=Depends(get_api_client)):
    if req.rating not in ("know", "dont_know", "skip"):
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail="Invalid rating")
    session = session_service.get_session_by_id(session_id)
    if session is None:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="Session not found")
    session = await session_service.rate_word(session, req.rating, api_client)
    word = session_service.get_current_word(session)
    if word is None:
        return {"session_id": session["session_id"], "card": None, "batch_exhausted": True}
    return _card_response(session)


@router.get("/{session_id}/progress")
async def get_progress(session_id: str):
    session = session_service.get_session_by_id(session_id)
    if session is None:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="Session not found")
    return session_service.get_progress(session)


@router.post("/{session_id}/next_batch")
async def next_batch(session_id: str, api_client=Depends(get_api_client)):
    session = session_service.get_session_by_id(session_id)
    if session is None:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="Session not found")
    loaded = await session_service.load_next_batch(session, api_client)
    if not loaded:
        return {"loaded": False, "session_id": session_id, "card": None}
    return {"loaded": True, **_card_response(session)}


@router.post("/{session_id}/know")
async def know_word(session_id: str, api_client=Depends(get_api_client)):
    session = session_service.get_session_by_id(session_id)
    if session is None:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="Session not found")
    session = await session_service.know_word(session, api_client)
    return _card_response(session)


@router.post("/{session_id}/reconsider")
async def reconsider_word(session_id: str, api_client=Depends(get_api_client)):
    session = session_service.get_session_by_id(session_id)
    if session is None:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="Session not found")
    session = await session_service.reconsider_word(session, api_client)
    session = await session_service.rate_word(session, "dont_know", api_client)
    word = session_service.get_current_word(session)
    if word is None:
        return {"session_id": session["session_id"], "card": None, "batch_exhausted": True}
    return _card_response(session)


@router.post("/{session_id}/toggle_skip")
async def toggle_skip(session_id: str, api_client=Depends(get_api_client)):
    session = session_service.get_session_by_id(session_id)
    if session is None:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="Session not found")
    session = await session_service.toggle_word_skip(session, api_client)
    return _card_response(session)


@router.delete("/{user_id}/{language_id}")
async def end_session(user_id: str, language_id: str):
    session_service.end_session(user_id, language_id)
    return {"ended": True}
