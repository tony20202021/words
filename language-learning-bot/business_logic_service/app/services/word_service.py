"""
Word/spaced-repetition business logic — no aiogram dependencies.
"""

from typing import Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from common.study_day import day_in_days
from app.logger import setup_logger

logger = setup_logger(__name__)

MAX_INTERVAL_DAYS = 32

# Отличает «документ не передавали» от «передали и там пусто»: во втором случае
# повторно ходить в backend не нужно, запись просто ещё не создана.
_NOT_FETCHED = object()


async def ensure_user_word_data(
    api_client,
    user_id: str,
    word_id: str,
    update_data: Dict[str, Any],
    word: Optional[Dict[str, Any]] = None,
    existing: Any = _NOT_FETCHED,
) -> Tuple[bool, Optional[Dict[str, Any]]]:
    """
    Create or update user word data. Returns (success, result_data).

    existing — уже прочитанный документ user_word_data (или None, если его нет).
    Передаётся вызывающим, который только что его получил, чтобы не делать
    второй такой же GET на ту же оценку слова.
    """
    if existing is _NOT_FETCHED:
        response = await api_client.get_user_word_data(user_id, word_id)
        logger.info(f"get_user_word_data user={user_id} word={word_id}: {response}")
        existing = response["result"] if response["success"] else None

    if existing:
        update_response = await api_client.update_user_word_data(user_id, word_id, update_data)
        logger.info(f"update_user_word_data: {update_response}")
        return update_response["success"], update_response.get("result")

    language_id = (word or {}).get("language_id")
    if not language_id:
        logger.error("Cannot create user word data: missing language_id")
        return False, None

    create_response = await api_client.create_user_word_data(user_id, {
        "word_id": word_id,
        "language_id": language_id,
        **update_data,
    })
    logger.info(f"create_user_word_data: {create_response}")
    return create_response["success"], create_response.get("result")


async def update_word_score(
    api_client,
    user_id: str,
    word_id: str,
    score: int,
    word: Dict[str, Any],
    is_skipped: bool = False,
    max_interval: int = MAX_INTERVAL_DAYS,
    timezone: str = "UTC",
    day_start_hour: int = 0,
) -> Tuple[bool, Optional[Dict[str, Any]]]:
    """Apply score to a word using spaced-repetition algorithm. Returns (success, result_data)."""
    logger.info(f"update_word_score user={user_id} word={word_id} score={score}")

    response = await api_client.get_user_word_data(user_id, word_id)
    if not response["success"]:
        logger.error(f"get_user_word_data failed: {response}")
        return False, None

    word_data: Dict[str, Any] = response["result"] or {}
    update_data = _calculate_update(word_data, score, is_skipped, max_interval,
                                    timezone=timezone, day_start_hour=day_start_hour)

    # Документ уже прочитан выше — передаём его дальше, иначе на каждую оценку
    # уходило два одинаковых GET /users/{u}/word_data/{w}.
    return await ensure_user_word_data(
        api_client, user_id, word_id, update_data, word, existing=response["result"]
    )


def _calculate_update(word_data: Dict[str, Any], score: int, is_skipped: bool,
                      max_interval: int = MAX_INTERVAL_DAYS,
                      timezone: str = "UTC", day_start_hour: int = 0) -> Dict[str, Any]:
    """Новые счёт, интервал и дата следующей проверки.

    Дата кладётся на границу учебных суток человека, а не на полночь UTC:
    тогда «пора ли повторять» остаётся обычным сравнением с текущим моментом,
    и ни бэкенд, ни запрос в Mongo про часовые пояса знать не обязаны.
    См. common/study_day.py.
    """
    update: Dict[str, Any] = {"score": score, "is_skipped": is_skipped}

    if score == 1:
        current_score = word_data.get("score", 0)
        current_interval = word_data.get("check_interval", 0)
        current_check_date_str = word_data.get("next_check_date")
        should_update = True

        if current_score == 1 and current_check_date_str:
            try:
                check_date = datetime.fromisoformat(current_check_date_str.replace("Z", ""))
                should_update = (datetime.utcnow() - check_date).days >= 0
            except (ValueError, TypeError):
                logger.warning(f"Could not parse check date: {current_check_date_str}")

        if should_update or current_score == 0:
            new_interval = max(1, min(current_interval * 2 if current_interval > 0 else 1, max_interval))
            new_check_date = day_in_days(
                new_interval, now_utc=datetime.utcnow(),
                timezone=timezone, day_start_hour=day_start_hour).isoformat()
            update["check_interval"] = new_interval
            update["next_check_date"] = new_check_date
        else:
            update["check_interval"] = current_interval
            update["next_check_date"] = current_check_date_str
    else:
        update["check_interval"] = 0
        # Ноль дней — значит «снова сегодня»: начало текущих учебных суток.
        update["next_check_date"] = day_in_days(
            0, now_utc=datetime.utcnow(),
            timezone=timezone, day_start_hour=day_start_hour).isoformat()

    return update
