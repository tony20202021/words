import asyncio
from datetime import date
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from starlette.status import HTTP_404_NOT_FOUND, HTTP_400_BAD_REQUEST
from typing import Optional, Dict, Any
from pydantic import BaseModel
from app.services import session_service, statistics_service
from app.services import quiz_service
from app.services.card_builder import build_card
from app.services.word_service import ensure_user_word_data
from app.api.client import get_api_client
from app.logger import setup_logger

logger = setup_logger(__name__)


async def _bg_update_daily(user_id: str, language_id: str, api_client, word_number: int = 0) -> None:
    """Update daily record and max_word_number after each word rating."""
    try:
        progress = await statistics_service.get_user_progress(user_id, language_id, api_client)
        today = date.today()
        await statistics_service.update_daily_statistics(
            user_id, language_id, today, progress, api_client)
        await statistics_service.update_daily_max_word_number(
            user_id, language_id, today, word_number, api_client)
    except Exception as e:
        logger.warning(f"bg daily stats update failed for {user_id}/{language_id}: {e}")


async def _bg_update_finish_on_unknown(user_id: str, language_id: str, api_client, incorrect_count: int) -> None:
    """Update finish stats on every 'don't know' answer.
    Uses session incorrect_count as words_unknown (not DB aggregation).
    first_finish keeps daily max; last_finish always overwrites."""
    try:
        today = date.today()
        progress = {"words_unknown": incorrect_count}
        await statistics_service.update_daily_first_finish_statistics(
            user_id, language_id, today, progress, api_client)
        await statistics_service.update_daily_last_finish_statistics(
            user_id, language_id, today, progress, api_client)
    except Exception as e:
        logger.warning(f"bg finish stats update failed for {user_id}/{language_id}: {e}")

router = APIRouter(prefix="/session", tags=["session"])


class StartSessionRequest(BaseModel):
    user_id: str
    language_id: str
    settings: Optional[Dict[str, Any]] = None
    session_mode: Optional[str] = None  # "normal" | "ignore_dates"


class RateRequest(BaseModel):
    rating: str  # "know" | "dont_know" | "skip"


class PickAnswerRequest(BaseModel):
    selected_word_id: str  # word_id of selected option, or "dont_know"


class ForbiddenPairRequest(BaseModel):
    bad_word_id: str  # word_id to add to forbidden pairs for current word


async def _card_response(session: Dict[str, Any], api_client=None) -> Dict[str, Any]:
    word = session_service.get_current_word(session)
    if word is None:
        return {"session_id": session["session_id"], "card": None, "no_words": True}
    show_answer = session.get("show_answer", False)

    # Generate quiz options lazily if pick mode is active and options not yet computed
    if (not show_answer and session.get("pick_mode_active") and
            not session.get("quiz_options") and api_client is not None):
        opts = await quiz_service.generate_quiz_options(session, word, api_client)
        if opts:
            session["quiz_options"] = opts
        else:
            # Fallback: disable pick mode for this word if we can't generate options
            session["pick_mode_active"] = False

    return {
        "session_id": session["session_id"],
        "card": build_card(session, word, show_answer),
    }


@router.post("/start")
async def start_session(req: StartSessionRequest, api_client=Depends(get_api_client)):
    session = await session_service.start_session(
        req.user_id, req.language_id, api_client, req.settings, req.session_mode
    )
    if session is None:
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail="Failed to start session")
    return await _card_response(session, api_client)


@router.get("/{user_id}/{language_id}")
async def get_session(user_id: str, language_id: str, api_client=Depends(get_api_client)):
    session = session_service.get_session(user_id, language_id)
    if session is None:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="No active session")
    resp = await _card_response(session, api_client)
    if session_service.is_session_expired(session):
        logger.info(f"Session stale for user={user_id} lang={language_id}")
        resp["session_stale"] = True
    return resp


@router.post("/{session_id}/show_answer")
async def show_answer(session_id: str,
                      background_tasks: BackgroundTasks,
                      api_client=Depends(get_api_client)):
    session = session_service.get_session_by_id(session_id)
    if session is None:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="Session not found")
    await session_service.show_answer_word(session, api_client)
    user_id = session.get("user_id", "")
    language_id = session.get("language_id", "")
    incorrect_count = session.get("incorrect_count", 0)
    background_tasks.add_task(_bg_update_finish_on_unknown, user_id, language_id, api_client, incorrect_count)
    return await _card_response(session, api_client)


@router.post("/{session_id}/rate")
async def rate_word(session_id: str, req: RateRequest,
                    background_tasks: BackgroundTasks,
                    api_client=Depends(get_api_client)):
    if req.rating not in ("know", "dont_know", "skip"):
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail="Invalid rating")
    session = session_service.get_session_by_id(session_id)
    if session is None:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="Session not found")
    user_id = session.get("user_id", "")
    language_id = session.get("language_id", "")
    rated_word = session_service.get_current_word(session)
    rated_wn = (rated_word or {}).get("word_number") or 0
    session = await session_service.rate_word(session, req.rating, api_client)
    session_service.touch_session(session)
    background_tasks.add_task(_bg_update_daily, user_id, language_id, api_client, rated_wn)
    if req.rating == "dont_know":
        incorrect_count = session.get("incorrect_count", 0)
        background_tasks.add_task(_bg_update_finish_on_unknown, user_id, language_id, api_client, incorrect_count)
    word = session_service.get_current_word(session)
    if word is None:
        return {"session_id": session["session_id"], "card": None, "batch_exhausted": True}
    return await _card_response(session, api_client)


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
    return {"loaded": True, **(await _card_response(session, api_client))}


@router.post("/{session_id}/know")
async def know_word(session_id: str,
                    background_tasks: BackgroundTasks,
                    api_client=Depends(get_api_client)):
    session = session_service.get_session_by_id(session_id)
    if session is None:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="Session not found")
    user_id = session.get("user_id", "")
    language_id = session.get("language_id", "")
    current_word = session_service.get_current_word(session)
    word_number = (current_word or {}).get("word_number") or 0
    session = await session_service.know_word(session, api_client)
    session_service.touch_session(session)
    background_tasks.add_task(_bg_update_daily, user_id, language_id, api_client, word_number)
    return await _card_response(session, api_client)


@router.post("/{session_id}/reconsider")
async def reconsider_word(session_id: str,
                          background_tasks: BackgroundTasks,
                          api_client=Depends(get_api_client)):
    session = session_service.get_session_by_id(session_id)
    if session is None:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="Session not found")
    user_id = session.get("user_id", "")
    language_id = session.get("language_id", "")
    session = await session_service.reconsider_word(session, api_client)
    session = await session_service.rate_word(session, "dont_know", api_client)
    incorrect_count = session.get("incorrect_count", 0)
    background_tasks.add_task(_bg_update_finish_on_unknown, user_id, language_id, api_client, incorrect_count)
    word = session_service.get_current_word(session)
    if word is None:
        return {"session_id": session["session_id"], "card": None, "batch_exhausted": True}
    return await _card_response(session, api_client)


@router.post("/{session_id}/pick_answer")
async def pick_answer(session_id: str, req: PickAnswerRequest,
                      background_tasks: BackgroundTasks,
                      api_client=Depends(get_api_client)):
    """Process a pick-mode (multiple-choice) answer."""
    session = session_service.get_session_by_id(session_id)
    if session is None:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="Session not found")

    user_id = session.get("user_id", "")
    language_id = session.get("language_id", "")
    current_word = session_service.get_current_word(session)
    word_number = (current_word or {}).get("word_number") or 0

    if req.selected_word_id == "dont_know":
        # Treat as "show answer" — score 0
        await session_service.show_answer_word(session, api_client)
        incorrect_count = session.get("incorrect_count", 0)
        background_tasks.add_task(_bg_update_finish_on_unknown, user_id, language_id, api_client, incorrect_count)
        session["pick_answer_result"] = "wrong"
    else:
        # Determine correctness from stored quiz options
        quiz_opts = session.get("quiz_options") or {}
        options = quiz_opts.get("options", [])
        correct_id = next((o["word_id"] for o in options if o.get("is_correct")), None)
        is_correct = (req.selected_word_id == correct_id)

        if is_correct:
            await session_service.know_word(session, api_client)
            background_tasks.add_task(_bg_update_daily, user_id, language_id, api_client, word_number)
            session["last_wrong_distractor_id"] = None
            session["pick_answer_was_used"] = True
            session["pick_answer_result"] = "correct"
        else:
            await session_service.show_answer_word(session, api_client)
            incorrect_count = session.get("incorrect_count", 0)
            background_tasks.add_task(_bg_update_finish_on_unknown, user_id, language_id, api_client, incorrect_count)
            # Store selected wrong distractor so card can show "ban this pair" button
            session["last_wrong_distractor_id"] = req.selected_word_id
            session["pick_answer_result"] = "wrong"

    session_service.touch_session(session)
    return await _card_response(session, api_client)


@router.post("/{session_id}/add_forbidden_pair")
async def add_forbidden_pair(session_id: str, req: ForbiddenPairRequest,
                             api_client=Depends(get_api_client)):
    """Add a word to the forbidden quiz pairs list for the current word."""
    session = session_service.get_session_by_id(session_id)
    if session is None:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="Session not found")

    word = session_service.get_current_word(session)
    if word is None:
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail="No current word")

    user_id = session.get("user_id", "")
    word_id = str(word.get("_id") or word.get("id") or word.get("word_id") or "")

    # Read current forbidden list, append, write back
    uwd = word.get("user_word_data") or {}
    forbidden = list(uwd.get("forbidden_quiz_pairs") or [])
    if req.bad_word_id not in forbidden:
        forbidden.append(req.bad_word_id)

    _, result = await ensure_user_word_data(
        api_client, user_id, word_id,
        {"forbidden_quiz_pairs": forbidden},
        word=word,
    )
    if result:
        if "user_word_data" not in word:
            word["user_word_data"] = {}
        word["user_word_data"]["forbidden_quiz_pairs"] = forbidden

    session["last_wrong_distractor_id"] = None
    return await _card_response(session, api_client)


@router.post("/{session_id}/clear_forbidden_pairs")
async def clear_forbidden_pairs(session_id: str, api_client=Depends(get_api_client)):
    """Clear all forbidden quiz pairs for the current word."""
    session = session_service.get_session_by_id(session_id)
    if session is None:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="Session not found")

    word = session_service.get_current_word(session)
    if word is None:
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail="No current word")

    user_id = session.get("user_id", "")
    word_id = str(word.get("_id") or word.get("id") or word.get("word_id") or "")

    _, result = await ensure_user_word_data(
        api_client, user_id, word_id,
        {"forbidden_quiz_pairs": []},
        word=word,
    )
    if result:
        if "user_word_data" not in word:
            word["user_word_data"] = {}
        word["user_word_data"]["forbidden_quiz_pairs"] = []

    return await _card_response(session, api_client)


@router.post("/{session_id}/toggle_skip")
async def toggle_skip(session_id: str, api_client=Depends(get_api_client)):
    session = session_service.get_session_by_id(session_id)
    if session is None:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="Session not found")
    session = await session_service.toggle_word_skip(session, api_client)
    return await _card_response(session, api_client)


@router.delete("/{user_id}/{language_id}")
async def end_session(user_id: str, language_id: str):
    session_service.end_session(user_id, language_id)
    return {"ended": True}
