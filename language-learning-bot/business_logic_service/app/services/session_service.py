"""
Study session business logic — no aiogram dependencies.
Sessions are stored in-memory (keyed by user_id + language_id).
Replace the _sessions store with Redis for multi-process deployments.
"""

import uuid
import random
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from app.logger import setup_logger
from app.services.word_service import update_word_score, MAX_INTERVAL_DAYS
from app.services.settings_service import get_settings

logger = setup_logger(__name__)

# In-memory session store: session_id → session dict
_sessions: Dict[str, Dict[str, Any]] = {}
# Index for fast lookup: (user_id, language_id) → session_id
_session_index: Dict[tuple, str] = {}

BATCH_SIZE = 100  # window of word numbers scanned per batch, matches Telegram bot


def _session_key(user_id: str, language_id: str) -> tuple:
    return (user_id, language_id)


def _pick_show_mode(settings: Dict[str, Any]) -> str:
    """Randomly pick what to show before the answer, based on user settings."""
    options = ["translation", "foreign"]  # always included
    if settings.get("random_transcription", True):
        options.append("transcription")
    if settings.get("random_sound", True) and settings.get("show_sounds", True):
        options.append("sound")
    return random.choice(options)


def _pick_quiz_mode(settings: Dict[str, Any]) -> bool:
    """Return True if this word should use pick mode (multiple-choice)."""
    return bool(settings.get("random_pick_mode", False)) and random.random() < 0.5


async def start_session(
    user_id: str,
    language_id: str,
    api_client,
    settings: Optional[Dict[str, Any]] = None,
    session_mode: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """
    Load words from backend and create a new study session.
    Returns the session dict or None on failure.
    """
    if settings is None:
        settings = await get_settings(user_id, language_id, api_client)

    if session_mode == "ignore_dates":
        settings = dict(settings)
        settings.update({"use_check_date": False, "skip_marked": False, "start_word": 1})

    start_shift = settings.get("start_word", 1)
    words, actual_shift = await _load_words_with_slide(api_client, user_id, language_id, settings, shift=start_shift)
    if not words and actual_shift > 10_000:
        return None

    progress = ((await api_client.get_user_progress(user_id, language_id)) or {}).get("result") or {}

    session_id = str(uuid.uuid4())
    session = {
        "session_id": session_id,
        "user_id": user_id,
        "language_id": language_id,
        "words": words,
        "current_index": 0,
        "batch_start": actual_shift,
        "total_words_processed": 0,
        "correct_count": 0,
        "incorrect_count": 0,
        "result_history": [],
        "active_hints": [],
        "used_hints": [],
        "word_processed": False,
        "show_answer": False,
        "score_changed": False,
        "settings": settings,
        "show_mode": _pick_show_mode(settings),
        "pick_mode_active": _pick_quiz_mode(settings),
        "quiz_options": None,
        "language_name_ru": progress.get("language_name_ru", ""),
        "language_name_foreign": progress.get("language_name_foreign", ""),
        "words_studied": progress.get("words_studied", 0),
        "total_words": progress.get("total_words", 0),
        "words_for_today": progress.get("words_for_today", 0),
    }

    session["last_activity_at"] = datetime.utcnow().isoformat()
    _sessions[session_id] = session
    _session_index[_session_key(user_id, language_id)] = session_id
    logger.info(f"Session started: {session_id} user={user_id} lang={language_id} words={len(words)}")
    return session


def get_session(user_id: str, language_id: str) -> Optional[Dict[str, Any]]:
    """Return active session for user+language, or None."""
    session_id = _session_index.get(_session_key(user_id, language_id))
    return _sessions.get(session_id) if session_id else None


def get_session_by_id(session_id: str) -> Optional[Dict[str, Any]]:
    return _sessions.get(session_id)


def is_session_expired(session: Dict[str, Any]) -> bool:
    """Return True if the session should be reset.

    Three-case logic based on calendar days elapsed:
      cal_days == 0: expired if total elapsed hours >= reset_same_day_hours (default 16)
      cal_days == 1: expired if current hour >= reset_cross_midnight_hours (default 6)
      cal_days >= 2: always expired

    Examples (defaults: same_day=16, midnight=6):
      same day, 4h elapsed                → not expired ✓
      same day, 17h elapsed               → expired ✓
      crossed midnight, now 02:00         → not expired ✓
      crossed midnight, now 06:00         → expired ✓
      2+ calendar days ago                → always expired ✓
    """
    last_activity = session.get("last_activity_at")
    if not last_activity:
        return False
    settings = session.get("settings", {})
    same_day_hours = int(settings.get("reset_same_day_hours", 16))
    midnight_hours = int(settings.get("reset_cross_midnight_hours", 6))
    last_dt = datetime.fromisoformat(last_activity)
    now = datetime.utcnow()
    cal_days = (now.date() - last_dt.date()).days
    if cal_days == 0:
        total_hours = (now - last_dt).total_seconds() / 3600
        return total_hours >= same_day_hours
    if cal_days == 1:
        return now.hour >= midnight_hours
    return True  # cal_days >= 2: always expired


def touch_session(session: Dict[str, Any]) -> None:
    """Update last_activity_at to now."""
    session["last_activity_at"] = datetime.utcnow().isoformat()


def get_current_word(session: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Return word dict at the current index, or None if exhausted."""
    words = session.get("words", [])
    idx = session.get("current_index", 0)
    if 0 <= idx < len(words):
        return words[idx]
    return None


async def rate_word(
    session: Dict[str, Any],
    rating: str,
    api_client,
) -> Dict[str, Any]:
    """
    Process a rating ('know' | 'dont_know' | 'skip') for the current word.
    Advances to the next word and returns updated session.
    """
    word = get_current_word(session)
    if word is None:
        return session

    user_id = session["user_id"]
    word_id = str(word.get("_id") or word.get("id") or word.get("word_id", ""))

    if not session.get("word_processed"):
        max_interval = int(session.get("settings", {}).get("max_check_interval", MAX_INTERVAL_DAYS))
        if rating == "know":
            await update_word_score(api_client, user_id, word_id, score=1, word=word, is_skipped=False, max_interval=max_interval)
            session["correct_count"] = session.get("correct_count", 0) + 1
        elif rating == "dont_know":
            await update_word_score(api_client, user_id, word_id, score=0, word=word, is_skipped=False, max_interval=max_interval)
            session["incorrect_count"] = session.get("incorrect_count", 0) + 1
        elif rating == "skip":
            await update_word_score(api_client, user_id, word_id, score=0, word=word, is_skipped=True, max_interval=max_interval)
        session["word_processed"] = True

    session.setdefault("result_history", []).append(rating)
    _advance(session)
    return session


async def load_next_batch(session: Dict[str, Any], api_client) -> bool:
    """
    Load the next batch of words when the current batch is exhausted.
    Slides the window forward (same as Telegram bot) until words are found.
    Returns True if new words were loaded.
    """
    settings = session.get("settings", {})
    shift = session["batch_start"] + BATCH_SIZE
    words, shift = await _load_words_with_slide(
        api_client, session["user_id"], session["language_id"], settings, shift
    )
    if not words:
        return False

    session["words"] = words
    session["current_index"] = 0
    session["batch_start"] = shift
    session["word_processed"] = False
    session["active_hints"] = []
    session["used_hints"] = []
    logger.info(f"Loaded next batch: {len(words)} words starting at {shift}")
    return True


def get_progress(session: Dict[str, Any]) -> Dict[str, Any]:
    """Return progress summary for the session."""
    words = session.get("words", [])
    idx = session.get("current_index", 0)
    total_processed = session.get("total_words_processed", 0)
    remaining = max(0, len(words) - idx)
    return {
        "session_id": session["session_id"],
        "current_index": idx,
        "batch_size": len(words),
        "remaining_in_batch": remaining,
        "total_words_processed": total_processed,
        "has_more": idx < len(words),
    }


async def know_word(session: Dict[str, Any], api_client) -> Dict[str, Any]:
    """
    Mark current word as known (score=1) and show result without advancing.
    Sets word_processed=True and score_changed=True so the card shows the new interval.
    Call rate_word("know") afterwards to advance — it will skip re-scoring.
    """
    word = get_current_word(session)
    if word is None or session.get("word_processed"):
        return session

    user_id = session["user_id"]
    word_id = str(word.get("_id") or word.get("id") or word.get("word_id", ""))

    uwd = (word or {}).get("user_word_data") or {}
    session["prev_score"] = uwd.get("score", -1)
    session["prev_interval"] = uwd.get("check_interval", 0)
    session["prev_next_check_date"] = uwd.get("next_check_date", "")

    max_interval = int(session.get("settings", {}).get("max_check_interval", MAX_INTERVAL_DAYS))
    success, result = await update_word_score(
        api_client, user_id, word_id, score=1, word=word, is_skipped=False, max_interval=max_interval
    )
    if success and result:
        if "user_word_data" not in word:
            word["user_word_data"] = {}
        word["user_word_data"].update(result)

    session["word_processed"] = True
    session["score_changed"] = True
    session["show_answer"] = True
    session["correct_count"] = session.get("correct_count", 0) + 1
    logger.info(f"Word marked as known: {word_id}")
    return session


async def show_answer_word(session: Dict[str, Any], api_client) -> Dict[str, Any]:
    """
    Mark answer as revealed and immediately record score=0.
    Sets word_processed=True so subsequent rate_word just advances without re-scoring.
    """
    if session.get("word_processed"):
        session["show_answer"] = True
        return session

    word = get_current_word(session)
    if word is None:
        session["show_answer"] = True
        return session

    user_id = session["user_id"]
    word_id = str(word.get("_id") or word.get("id") or word.get("word_id", ""))

    uwd = (word or {}).get("user_word_data") or {}
    session["prev_score"] = uwd.get("score", -1)
    session["prev_interval"] = uwd.get("check_interval", 0)
    session["prev_next_check_date"] = uwd.get("next_check_date", "")

    max_interval = int(session.get("settings", {}).get("max_check_interval", MAX_INTERVAL_DAYS))
    success, result = await update_word_score(
        api_client, user_id, word_id, score=0, word=word, is_skipped=False, max_interval=max_interval
    )
    if success and result:
        if "user_word_data" not in word:
            word["user_word_data"] = {}
        word["user_word_data"].update(result)

    session["word_processed"] = True
    session["show_answer"] = True
    session["incorrect_count"] = session.get("incorrect_count", 0) + 1
    logger.info(f"Word marked as unknown: {word_id}")
    return session


async def reconsider_word(session: Dict[str, Any], api_client) -> Dict[str, Any]:
    """
    User said 'know' but reconsiders — overwrite score to 0.
    Adjusts counters: correct_count-1, incorrect_count+1.
    Keeps word_processed=True so rate_word won't re-score.
    """
    if not session.get("score_changed"):
        return session

    word = get_current_word(session)
    if word is None:
        return session

    user_id = session["user_id"]
    word_id = str(word.get("_id") or word.get("id") or word.get("word_id", ""))

    max_interval = int(session.get("settings", {}).get("max_check_interval", MAX_INTERVAL_DAYS))
    success, result = await update_word_score(
        api_client, user_id, word_id, score=0, word=word, is_skipped=False, max_interval=max_interval
    )
    if success and result:
        if "user_word_data" not in word:
            word["user_word_data"] = {}
        word["user_word_data"].update(result)

    session["score_changed"] = False
    session["correct_count"] = max(0, session.get("correct_count", 0) - 1)
    session["incorrect_count"] = session.get("incorrect_count", 0) + 1
    logger.info(f"Word reconsidered (know→dont_know): {word_id}")
    return session


async def toggle_word_skip(session: Dict[str, Any], api_client) -> Dict[str, Any]:
    """
    Toggle is_skipped on the current word. Does not advance the session.
    Returns updated session.
    """
    from app.services.word_service import ensure_user_word_data

    word = get_current_word(session)
    if word is None:
        return session

    user_id = session["user_id"]
    word_id = str(word.get("_id") or word.get("id") or word.get("word_id", ""))
    uwd = word.get("user_word_data") or {}
    new_skip = not uwd.get("is_skipped", False)

    success, result = await ensure_user_word_data(
        api_client, user_id, word_id, {"is_skipped": new_skip}, word=word
    )
    if success:
        if "user_word_data" not in word:
            word["user_word_data"] = {}
        word["user_word_data"]["is_skipped"] = new_skip
        logger.info(f"Toggled skip word={word_id} is_skipped={new_skip}")

    return session


def end_session(user_id: str, language_id: str) -> None:
    """Remove session from store."""
    key = _session_key(user_id, language_id)
    session_id = _session_index.pop(key, None)
    if session_id:
        _sessions.pop(session_id, None)
        logger.info(f"Session ended: {session_id}")


# ── internals ─────────────────────────────────────────────────────────────────

def _advance(session: Dict[str, Any]) -> None:
    settings = session.get("settings", {})
    session["current_index"] += 1
    session["total_words_processed"] += 1
    session["word_processed"] = False
    session["score_changed"] = False
    session["show_answer"] = False
    session["active_hints"] = []
    session["used_hints"] = []
    session["show_mode"] = _pick_show_mode(settings)
    session["pick_mode_active"] = _pick_quiz_mode(settings)
    session["quiz_options"] = None
    session["pick_answer_was_used"] = False


async def _load_words_with_slide(
    api_client,
    user_id: str,
    language_id: str,
    settings: Dict[str, Any],
    shift: int,
    max_shift: int = 10_000,
) -> tuple:
    """
    Slide the window forward (BATCH_SIZE steps) until words are found or max_shift reached.
    Mirrors Telegram bot's while-loop in load_next_batch.
    Returns (words_list, actual_shift_used).
    """
    current_shift = shift or settings.get("start_word", 1)
    while current_shift <= max_shift:
        params = {
            "start_word": current_shift,
            "skip_marked": settings.get("skip_marked", True),
            "use_check_date": settings.get("use_check_date", True),
        }
        response = await api_client.get_study_words(
            user_id=user_id,
            language_id=language_id,
            params=params,
            limit=BATCH_SIZE,
        )
        if not response["success"]:
            logger.error(f"Failed to load words user={user_id} lang={language_id}: {response}")
            return [], current_shift

        words = response.get("result") or []
        if words:
            logger.info(f"Found {len(words)} words at shift={current_shift}")
            return words, current_shift

        logger.info(f"No words at shift={current_shift}, sliding to {current_shift + BATCH_SIZE}")
        current_shift += BATCH_SIZE

    logger.info(f"No words found up to max_shift={max_shift}")
    return [], current_shift
